"""
train_deep_v3.py
-------------------
train_deep_v2.py와 특성/구조는 동일하지만, **라벨 정의 자체**가 확장된
data/risk_training_data_v3.csv (build_dataset_v3.py 산출물)를 씁니다.

v2까지는 label = 1 if danger_count > 0 else 0 (즉 drug_conflict 하나로
사실상 결정)이었고, 그 결과 순열 중요도를 재보면 drug_conflict 혼자
F1의 86%p를 차지하고 나머지 6개 특성(v2에서 새로 추가한 2개 포함)은
거의 기여가 없었습니다 -- 특성이 아무리 좋아도 라벨이 그걸 안 쓰면
모델이 배울 수 없기 때문입니다.

v3는 라벨에 3가지 임상적 기준을 추가했습니다 (OR 조건 -- 자세한 근거는
build_dataset_v3.py 문서와 이 저장소 README.md 참고):
  - 과다다약제 (매칭 약물 10종 이상)
  - 중증(SEVERE) 약물 알레르기/불내성 이력
  - 주의 알림 3개 이상 누적

data/risk_training_data_v3.csv (86,116행)를 씁니다.
"""

import csv
import random

import torch
import torch.nn as nn


class RiskDeepMLPv3(nn.Module):
    def __init__(self, in_dim: int = 7, hidden=(128, 64, 32, 16, 8), dropout: float = 0.25):
        super().__init__()
        layers = []
        prev = in_dim
        for h in hidden:
            layers += [nn.Linear(prev, h), nn.BatchNorm1d(h), nn.ReLU(), nn.Dropout(dropout)]
            prev = h
        layers += [nn.Linear(prev, 1), nn.Sigmoid()]
        self.net = nn.Sequential(*layers)

    def forward(self, x):
        return self.net(x).squeeze(-1)


FEATURES = [
    "drug_conflict", "comorbidity_load", "age_risk", "allergy_flag",
    "adverse_history", "polypharmacy_load", "therapy_duration_load",
]
# allergy_flag(인덱스 3)만 이진값이라 지터에서 제외. 나머지 6개는 전부
# 실제로 연속적인 값이라 지터를 적용해도 안전함 (v1의 지터 버그 -- 상수
# 특성에 지터를 섞어 모델이 편법을 학습한 문제 -- 가 여기선 재발하지 않음).
JITTER_DIMS = [0, 1, 2, 4, 5, 6]


def load_data(path):
    xs, ys = [], []
    with open(path, encoding="utf-8") as f:
        for row in csv.DictReader(f):
            xs.append([float(row[k]) for k in FEATURES])
            ys.append(float(row["label"]))
    return torch.tensor(xs, dtype=torch.float32), torch.tensor(ys, dtype=torch.float32)


def stratified_split(x, y, val_frac=0.2, seed=0):
    random.seed(seed)
    pos_idx = [i for i, v in enumerate(y) if v == 1]
    neg_idx = [i for i, v in enumerate(y) if v == 0]
    random.shuffle(pos_idx)
    random.shuffle(neg_idx)
    n_val_pos = max(1, int(len(pos_idx) * val_frac))
    n_val_neg = int(len(neg_idx) * val_frac)
    val_idx = pos_idx[:n_val_pos] + neg_idx[:n_val_neg]
    train_idx = pos_idx[n_val_pos:] + neg_idx[n_val_neg:]
    random.shuffle(train_idx)
    random.shuffle(val_idx)
    return x[train_idx], y[train_idx], x[val_idx], y[val_idx]


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


def metrics(pred, y, threshold=0.5):
    pred_label = (pred > threshold).float()
    tp = ((pred_label == 1) & (y == 1)).sum().item()
    fp = ((pred_label == 1) & (y == 0)).sum().item()
    fn = ((pred_label == 0) & (y == 1)).sum().item()
    tn = ((pred_label == 0) & (y == 0)).sum().item()
    precision = tp / (tp + fp) if (tp + fp) else 0.0
    recall = tp / (tp + fn) if (tp + fn) else 0.0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) else 0.0
    acc = (tp + tn) / len(y)
    return {"acc": acc, "precision": precision, "recall": recall, "f1": f1, "tp": tp, "fp": fp, "fn": fn, "tn": tn}


def train(data_path="data/risk_training_data_v3.csv", hidden=(128, 64, 32, 16, 8), dropout=0.25,
          epochs=250, lr=0.01, target_positive_count=17000, batch_size=256):
    x, y = load_data(data_path)
    x_train, y_train, x_val, y_val = stratified_split(x, y)
    n_before = int(y_train.sum())
    x_train, y_train = oversample_positives(x_train, y_train, target_positive_count)
    n_after = int(y_train.sum())
    print(f"train: {len(x_train)} total, 고위험 {n_before} -> 오버샘플링 후 {n_after}")
    print(f"val (자연분포, 손대지 않음): {len(x_val)} total, 고위험 {int(y_val.sum())}")

    model = RiskDeepMLPv3(hidden=hidden, dropout=dropout)
    optimizer = torch.optim.Adam(model.parameters(), lr=lr)
    scheduler = torch.optim.lr_scheduler.StepLR(optimizer, step_size=70, gamma=0.5)
    loss_fn = nn.BCELoss()

    n = len(x_train)
    best_f1, best_state = -1.0, None
    for epoch in range(1, epochs + 1):
        model.train()
        perm = torch.randperm(n)
        total_loss = 0.0
        for i in range(0, n, batch_size):
            idx = perm[i : i + batch_size]
            if len(idx) < 2:
                continue  # BatchNorm1d needs >1 sample per batch in train mode
            optimizer.zero_grad()
            pred = model(x_train[idx])
            loss = loss_fn(pred, y_train[idx])
            loss.backward()
            optimizer.step()
            total_loss += loss.item() * len(idx)
        scheduler.step()

        if epoch % 25 == 0 or epoch == epochs:
            model.eval()
            with torch.no_grad():
                val_pred = model(x_val)
                m = metrics(val_pred, y_val)
            if m["f1"] > best_f1:
                best_f1, best_state = m["f1"], {k: v.clone() for k, v in model.state_dict().items()}
            print(
                f"epoch {epoch:3d}  lr={scheduler.get_last_lr()[0]:.4f}  train_loss={total_loss/n:.4f}  "
                f"val_acc={m['acc']*100:.1f}%  val_precision={m['precision']*100:.1f}%  "
                f"val_recall={m['recall']*100:.1f}%  val_f1={m['f1']*100:.1f}%  "
                f"(TP={m['tp']:.0f} FP={m['fp']:.0f} FN={m['fn']:.0f} TN={m['tn']:.0f})"
            )

    if best_state is not None:
        model.load_state_dict(best_state)
    return model, x_val, y_val


def export_onnx(model, path="risk_model_deep_v3.onnx"):
    model.eval()
    dummy = torch.zeros(1, len(FEATURES), dtype=torch.float32)
    torch.onnx.export(
        model, dummy, path,
        input_names=["features"], output_names=["risk_probability"],
        dynamic_axes={"features": {0: "batch"}, "risk_probability": {0: "batch"}},
        opset_version=13, dynamo=False,
    )
    print(f"ONNX 저장 완료: {path}")


if __name__ == "__main__":
    model, x_val, y_val = train()
    torch.save(model.state_dict(), "risk_model_deep_v3.pt")
    export_onnx(model)
