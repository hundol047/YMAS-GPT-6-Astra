"""
train_deep.py
---------------
YMAS(SynexAgent) 저장소 backend/train_with_oversampling.py의 얕은 모델
(입력5 -> 은닉8 -> 출력1, 파라미터 57개)을 다층 구조로 확장한 딥러닝 버전.
학습 데이터는 이 저장소의 data/risk_training_data.csv를 씁니다
(원본 real_dataset.json을 export_csv.py로 CSV 하나로 통합한 것 --
자세한 배경은 YMAS 저장소의 backend/REAL_DATA_MODEL.md 참고).

v7과의 차이:
  1. **구조**: 1개 은닉층 -> 4개 은닉층(64-32-16-8), 각 층마다
     BatchNorm + ReLU + Dropout을 적용한 진짜 다층 신경망입니다.
  2. **오버샘플링 버그 수정**: v7은 클래스 불균형 보정을 위해 "위험" 샘플을
     복제할 때 5개 특성 전부에 지터(잡음)를 더했습니다. 그런데
     `adverse_history`(과거 부작용 이력)는 이 데이터셋 116,262명 전원이
     0.0으로, 실제로는 값이 전혀 변하지 않는 상수 특성입니다. 여기에
     지터를 섞으면 "0보다 살짝만 커도 무조건 위험"이라는, 임상적으로
     아무 의미 없는 지름길을 모델이 학습해버립니다(실측: 무작위 조합
     200개 중 200개가 adverse_history=0.1만으로 전부 위험 판정됨).
     이 버전은 `allergy_flag`, `adverse_history`처럼 이진/상수에 가까운
     특성은 지터에서 제외하고, 실제로 연속적인 3개 특성(drug_conflict,
     comorbidity_load, age_risk)에만 지터를 적용합니다.

여전히 남은 한계(정직하게): `adverse_history`는 이 데이터셋에서 여전히
상수 0이라 모델이 학습할 신호 자체가 없습니다. 근본적으로 고치려면
Synthea allergies.csv의 SEVERITY1/SEVERITY2(실제 중증도 값)를 이용해
이 특성을 다시 계산해야 하며, 그러려면 Synthea를 다시 돌려야 합니다
(원본 raw CSV는 디스크 절약을 위해 이미 삭제됨). 이번 버전은 그 작업
전, "구조를 딥러닝으로 바꾸고 확실한 버그(지터)만 고친" 중간 단계입니다.
"""

import csv
import random

import torch
import torch.nn as nn


class RiskDeepMLP(nn.Module):
    def __init__(self, in_dim: int = 5, hidden=(64, 32, 16, 8), dropout: float = 0.2):
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


FEATURES = ["drug_conflict", "comorbidity_load", "age_risk", "allergy_flag", "adverse_history"]
# 지터를 적용할 특성의 인덱스만 (연속값 3개 -- 이진/상수 특성인 allergy_flag,
# adverse_history는 제외: 위 docstring의 버그 수정 내용 참고)
JITTER_DIMS = [0, 1, 2]


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


def train(data_path="data/risk_training_data.csv", hidden=(64, 32, 16, 8), dropout=0.2,
          epochs=200, lr=0.01, target_positive_count=18000, batch_size=256):
    x, y = load_data(data_path)
    x_train, y_train, x_val, y_val = stratified_split(x, y)
    n_before = int(y_train.sum())
    x_train, y_train = oversample_positives(x_train, y_train, target_positive_count)
    n_after = int(y_train.sum())
    print(f"train: {len(x_train)} total, 고위험 {n_before} -> 오버샘플링 후 {n_after}")
    print(f"val (자연분포, 손대지 않음): {len(x_val)} total, 고위험 {int(y_val.sum())}")

    model = RiskDeepMLP(hidden=hidden, dropout=dropout)
    optimizer = torch.optim.Adam(model.parameters(), lr=lr)
    scheduler = torch.optim.lr_scheduler.StepLR(optimizer, step_size=60, gamma=0.5)
    loss_fn = nn.BCELoss()

    n = len(x_train)
    best_f1, best_state = -1.0, None
    for epoch in range(1, epochs + 1):
        model.train()
        perm = torch.randperm(n)
        total_loss = 0.0
        for i in range(0, n, batch_size):
            idx = perm[i : i + batch_size]
            optimizer.zero_grad()
            pred = model(x_train[idx])
            loss = loss_fn(pred, y_train[idx])
            loss.backward()
            optimizer.step()
            total_loss += loss.item() * len(idx)
        scheduler.step()

        if epoch % 20 == 0 or epoch == epochs:
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


def export_onnx(model, path="risk_model_deep.onnx"):
    model.eval()
    dummy = torch.zeros(1, 5, dtype=torch.float32)
    torch.onnx.export(
        model, dummy, path,
        input_names=["features"], output_names=["risk_probability"],
        dynamic_axes={"features": {0: "batch"}, "risk_probability": {0: "batch"}},
        opset_version=13, dynamo=False,
    )
    print(f"ONNX 저장 완료: {path}")


if __name__ == "__main__":
    model, x_val, y_val = train()
    torch.save(model.state_dict(), "risk_model_deep.pt")
    export_onnx(model)
