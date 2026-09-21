"""
crossval_v3.py
----------------
train_deep_v3.py는 seed=0으로 고정된 단일 train/val 분할(80/20)만 씁니다.
v3의 검증 F1이 100%로 나온 게 "이 분할에서만 우연히 그런 건 아닌가"를
확인하기 위해, 5-fold 교차검증으로 다른 4개 분할에서도 재현되는지
검증합니다.

각 fold는 독립적으로 오버샘플링 -> 학습 -> (그 fold의) 검증셋 평가를
반복합니다. train_deep_v3.py와 동일한 하이퍼파라미터를 씁니다.

사용법: python3 crossval_v3.py
"""

import csv
import random

import torch
import torch.nn as nn

from train_deep_v3 import RiskDeepMLPv3, FEATURES, JITTER_DIMS, metrics


def load_data(path):
    xs, ys = [], []
    with open(path, encoding="utf-8") as f:
        for row in csv.DictReader(f):
            xs.append([float(row[k]) for k in FEATURES])
            ys.append(float(row["label"]))
    return torch.tensor(xs, dtype=torch.float32), torch.tensor(ys, dtype=torch.float32)


def kfold_indices(y, k, seed):
    random.seed(seed)
    pos_idx = [i for i, v in enumerate(y) if v == 1]
    neg_idx = [i for i, v in enumerate(y) if v == 0]
    random.shuffle(pos_idx)
    random.shuffle(neg_idx)

    def chunks(lst, k):
        return [lst[i::k] for i in range(k)]

    pos_folds = chunks(pos_idx, k)
    neg_folds = chunks(neg_idx, k)
    for i in range(k):
        val_idx = pos_folds[i] + neg_folds[i]
        train_idx = [j for f in range(k) if f != i for j in (pos_folds[f] + neg_folds[f])]
        random.shuffle(train_idx)
        random.shuffle(val_idx)
        yield train_idx, val_idx


def oversample_positives(x_train, y_train, target_positive_count, jitter=0.03, seed=0):
    random.seed(seed)
    torch.manual_seed(seed)
    pos_mask = y_train == 1
    pos_x = x_train[pos_mask]
    n_have = pos_x.size(0)
    if n_have >= target_positive_count:
        return x_train, y_train
    n_needed = target_positive_count - n_have
    idx = torch.randint(0, n_have, (n_needed,))
    noise = torch.zeros(n_needed, pos_x.size(1))
    jitter_noise = (torch.rand(n_needed, len(JITTER_DIMS)) - 0.5) * 2 * jitter
    noise[:, JITTER_DIMS] = jitter_noise
    synth = torch.clamp(pos_x[idx] + noise, 0.0, 1.0)
    x_out = torch.cat([x_train, synth], dim=0)
    y_out = torch.cat([y_train, torch.ones(n_needed)], dim=0)
    perm = torch.randperm(x_out.size(0))
    return x_out[perm], y_out[perm]


def train_one_fold(x_train, y_train, x_val, y_val, hidden=(128, 64, 32, 16, 8), dropout=0.25,
                    epochs=250, lr=0.01, target_positive_count=17000, batch_size=256, seed=0):
    torch.manual_seed(seed)
    x_train, y_train = oversample_positives(x_train, y_train, target_positive_count, seed=seed)

    model = RiskDeepMLPv3(hidden=hidden, dropout=dropout)
    optimizer = torch.optim.Adam(model.parameters(), lr=lr)
    scheduler = torch.optim.lr_scheduler.StepLR(optimizer, step_size=70, gamma=0.5)
    loss_fn = nn.BCELoss()

    n = len(x_train)
    best_f1, best_state = -1.0, None
    for epoch in range(1, epochs + 1):
        model.train()
        perm = torch.randperm(n)
        for i in range(0, n, batch_size):
            idx = perm[i : i + batch_size]
            if len(idx) < 2:
                continue  # BatchNorm1d needs >1 sample per batch in train mode
            optimizer.zero_grad()
            pred = model(x_train[idx])
            loss = loss_fn(pred, y_train[idx])
            loss.backward()
            optimizer.step()
        scheduler.step()
        if epoch % 25 == 0 or epoch == epochs:
            model.eval()
            with torch.no_grad():
                m = metrics(model(x_val), y_val)
            if m["f1"] > best_f1:
                best_f1, best_state = m["f1"], {k: v.clone() for k, v in model.state_dict().items()}
    if best_state is not None:
        model.load_state_dict(best_state)
    model.eval()
    with torch.no_grad():
        final_m = metrics(model(x_val), y_val)
    return final_m


if __name__ == "__main__":
    x, y = load_data("data/risk_training_data_v3.csv")
    print(f"전체 {len(x)}행, 고위험 {int(y.sum())}명 ({y.mean()*100:.1f}%)")
    print("5-fold 교차검증 시작 (fold별로 완전히 다른 20%를 검증셋으로 사용)\n")

    results = []
    for fold, (train_idx, val_idx) in enumerate(kfold_indices(y, k=5, seed=1)):
        x_train, y_train = x[train_idx], y[train_idx]
        x_val, y_val = x[val_idx], y[val_idx]
        m = train_one_fold(x_train, y_train, x_val, y_val, seed=fold)
        results.append(m)
        print(
            f"fold {fold+1}/5  val_n={len(val_idx)} (고위험 {int(y_val.sum())})  "
            f"acc={m['acc']*100:.2f}%  precision={m['precision']*100:.2f}%  "
            f"recall={m['recall']*100:.2f}%  f1={m['f1']*100:.2f}%  "
            f"(TP={m['tp']:.0f} FP={m['fp']:.0f} FN={m['fn']:.0f} TN={m['tn']:.0f})"
        )

    print("\n=== 5-fold 평균 ===")
    for key in ["acc", "precision", "recall", "f1"]:
        vals = [r[key] for r in results]
        mean = sum(vals) / len(vals)
        std = (sum((v - mean) ** 2 for v in vals) / len(vals)) ** 0.5
        print(f"{key:10s} 평균={mean*100:.2f}%  표준편차={std*100:.2f}%p  (fold별: {[round(v*100,2) for v in vals]})")
