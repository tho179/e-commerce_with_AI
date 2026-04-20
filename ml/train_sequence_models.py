import copy
import json
import random
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
import torch
import torch.nn as nn
from sklearn.metrics import (
    accuracy_score,
    confusion_matrix,
    precision_recall_fscore_support,
)
from sklearn.model_selection import train_test_split
from torch.utils.data import DataLoader, Dataset


SEED = 42
SEQ_LEN = 3
BATCH_SIZE = 64
EPOCHS = 30
PATIENCE = 6
LEARNING_RATE = 1e-3


def set_seed(seed: int) -> None:
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)


class SequenceDataset(Dataset):
    def __init__(self, action_seq, product_seq, time_seq, targets):
        self.action_seq = torch.tensor(action_seq, dtype=torch.long)
        self.product_seq = torch.tensor(product_seq, dtype=torch.long)
        self.time_seq = torch.tensor(time_seq, dtype=torch.float32)
        self.targets = torch.tensor(targets, dtype=torch.long)

    def __len__(self):
        return len(self.targets)

    def __getitem__(self, idx):
        return (
            self.action_seq[idx],
            self.product_seq[idx],
            self.time_seq[idx],
            self.targets[idx],
        )


class ActionSequenceModel(nn.Module):
    def __init__(
        self,
        model_type,
        num_actions,
        num_products,
        time_dim,
        action_emb_dim=8,
        product_emb_dim=16,
        hidden_dim=64,
        dropout=0.2,
    ):
        super().__init__()
        self.model_type = model_type
        self.action_emb = nn.Embedding(num_actions, action_emb_dim)
        self.product_emb = nn.Embedding(num_products, product_emb_dim)

        input_dim = action_emb_dim + product_emb_dim + time_dim

        if model_type == "RNN":
            self.recurrent = nn.RNN(
                input_size=input_dim,
                hidden_size=hidden_dim,
                batch_first=True,
                nonlinearity="tanh",
            )
            out_dim = hidden_dim
        elif model_type == "LSTM":
            self.recurrent = nn.LSTM(
                input_size=input_dim,
                hidden_size=hidden_dim,
                batch_first=True,
            )
            out_dim = hidden_dim
        elif model_type == "biLSTM":
            self.recurrent = nn.LSTM(
                input_size=input_dim,
                hidden_size=hidden_dim,
                batch_first=True,
                bidirectional=True,
            )
            out_dim = hidden_dim * 2
        else:
            raise ValueError(f"Unsupported model_type: {model_type}")

        self.classifier = nn.Sequential(
            nn.Linear(out_dim, 64),
            nn.ReLU(),
            nn.Dropout(dropout),
            nn.Linear(64, num_actions),
        )

    def forward(self, action_seq, product_seq, time_seq):
        action_vec = self.action_emb(action_seq)
        product_vec = self.product_emb(product_seq)
        x = torch.cat([action_vec, product_vec, time_seq], dim=-1)
        recurrent_out, _ = self.recurrent(x)
        last_hidden = recurrent_out[:, -1, :]
        return self.classifier(last_hidden)


def compute_metrics(y_true, y_pred):
    precision, recall, f1, _ = precision_recall_fscore_support(
        y_true,
        y_pred,
        average="macro",
        zero_division=0,
    )
    return {
        "accuracy": accuracy_score(y_true, y_pred),
        "macro_precision": precision,
        "macro_recall": recall,
        "macro_f1": f1,
    }


def run_epoch(model, loader, criterion, optimizer, device, train_mode=True):
    if train_mode:
        model.train()
    else:
        model.eval()

    all_preds = []
    all_targets = []
    running_loss = 0.0

    for action_seq, product_seq, time_seq, targets in loader:
        action_seq = action_seq.to(device)
        product_seq = product_seq.to(device)
        time_seq = time_seq.to(device)
        targets = targets.to(device)

        if train_mode:
            optimizer.zero_grad()

        with torch.set_grad_enabled(train_mode):
            logits = model(action_seq, product_seq, time_seq)
            loss = criterion(logits, targets)
            if train_mode:
                loss.backward()
                optimizer.step()

        running_loss += loss.item() * targets.size(0)
        preds = torch.argmax(logits, dim=1)
        all_preds.extend(preds.detach().cpu().numpy().tolist())
        all_targets.extend(targets.detach().cpu().numpy().tolist())

    avg_loss = running_loss / len(loader.dataset)
    metrics = compute_metrics(np.array(all_targets), np.array(all_preds))
    return avg_loss, metrics


def evaluate_model(model, loader, criterion, device):
    model.eval()
    all_preds = []
    all_targets = []
    running_loss = 0.0

    with torch.no_grad():
        for action_seq, product_seq, time_seq, targets in loader:
            action_seq = action_seq.to(device)
            product_seq = product_seq.to(device)
            time_seq = time_seq.to(device)
            targets = targets.to(device)

            logits = model(action_seq, product_seq, time_seq)
            loss = criterion(logits, targets)

            running_loss += loss.item() * targets.size(0)
            preds = torch.argmax(logits, dim=1)
            all_preds.extend(preds.detach().cpu().numpy().tolist())
            all_targets.extend(targets.detach().cpu().numpy().tolist())

    avg_loss = running_loss / len(loader.dataset)
    metrics = compute_metrics(np.array(all_targets), np.array(all_preds))
    return avg_loss, metrics, np.array(all_targets), np.array(all_preds)


def build_sequences(df, seq_len):
    action_values = sorted(df["action"].unique().tolist())
    product_values = sorted(df["product_id"].unique().tolist())

    action_to_idx = {action: idx for idx, action in enumerate(action_values)}
    product_to_idx = {product: idx for idx, product in enumerate(product_values)}

    df = df.copy()
    df["action_idx"] = df["action"].map(action_to_idx)
    df["product_idx"] = df["product_id"].map(product_to_idx)

    dt = pd.to_datetime(df["timestamp"], utc=True)
    df["hour_sin"] = np.sin(2 * np.pi * dt.dt.hour / 24.0)
    df["hour_cos"] = np.cos(2 * np.pi * dt.dt.hour / 24.0)
    df["dow_sin"] = np.sin(2 * np.pi * dt.dt.dayofweek / 7.0)
    df["dow_cos"] = np.cos(2 * np.pi * dt.dt.dayofweek / 7.0)

    action_seq = []
    product_seq = []
    time_seq = []
    targets = []

    grouped = df.sort_values(["user_id", "timestamp"]).groupby("user_id")

    for _, g in grouped:
        g = g.reset_index(drop=True)
        if len(g) <= seq_len:
            continue
        for i in range(seq_len, len(g)):
            context = g.iloc[i - seq_len : i]
            action_seq.append(context["action_idx"].to_numpy())
            product_seq.append(context["product_idx"].to_numpy())
            time_seq.append(
                context[["hour_sin", "hour_cos", "dow_sin", "dow_cos"]].to_numpy(dtype=np.float32)
            )
            targets.append(int(g.iloc[i]["action_idx"]))

    return {
        "action_seq": np.array(action_seq),
        "product_seq": np.array(product_seq),
        "time_seq": np.array(time_seq),
        "targets": np.array(targets),
        "action_to_idx": action_to_idx,
        "idx_to_action": {idx: action for action, idx in action_to_idx.items()},
        "num_products": len(product_values),
    }


def plot_training_curve(history, model_name, output_dir):
    epochs = np.arange(1, len(history["train_loss"]) + 1)

    fig, axes = plt.subplots(1, 2, figsize=(12, 4.5))
    axes[0].plot(epochs, history["train_loss"], label="Train Loss")
    axes[0].plot(epochs, history["val_loss"], label="Val Loss")
    axes[0].set_title(f"{model_name} Loss")
    axes[0].set_xlabel("Epoch")
    axes[0].set_ylabel("Loss")
    axes[0].legend()
    axes[0].grid(alpha=0.25)

    axes[1].plot(epochs, history["train_acc"], label="Train Accuracy")
    axes[1].plot(epochs, history["val_acc"], label="Val Accuracy")
    axes[1].set_title(f"{model_name} Accuracy")
    axes[1].set_xlabel("Epoch")
    axes[1].set_ylabel("Accuracy")
    axes[1].legend()
    axes[1].grid(alpha=0.25)

    fig.tight_layout()
    fig.savefig(output_dir / f"curve_{model_name}.png", dpi=150)
    plt.close(fig)


def plot_metric_comparison(results_df, output_dir):
    metric_columns = ["accuracy", "macro_precision", "macro_recall", "macro_f1"]
    plot_df = results_df.set_index("model")[metric_columns]

    fig, ax = plt.subplots(figsize=(10, 5))
    plot_df.plot(kind="bar", ax=ax)
    ax.set_ylim(0.0, 1.0)
    ax.set_ylabel("Score")
    ax.set_title("Test Metric Comparison: RNN vs LSTM vs biLSTM")
    ax.grid(axis="y", alpha=0.2)
    fig.tight_layout()
    fig.savefig(output_dir / "metric_comparison.png", dpi=150)
    plt.close(fig)


def plot_confusion(y_true, y_pred, idx_to_action, model_name, output_dir):
    labels = [idx_to_action[i] for i in sorted(idx_to_action)]
    cm = confusion_matrix(y_true, y_pred, labels=list(range(len(labels))))

    fig, ax = plt.subplots(figsize=(8.5, 7))
    sns.heatmap(cm, annot=True, fmt="d", cmap="Blues", xticklabels=labels, yticklabels=labels, ax=ax)
    ax.set_title(f"Confusion Matrix ({model_name})")
    ax.set_xlabel("Predicted")
    ax.set_ylabel("True")
    fig.tight_layout()
    fig.savefig(output_dir / "confusion_matrix_best.png", dpi=150)
    plt.close(fig)


def main():
    set_seed(SEED)
    sns.set_theme(style="whitegrid")

    project_root = Path(__file__).resolve().parents[1]
    data_path = project_root / "data_user500.csv"
    output_dir = project_root / "ml_outputs"
    output_dir.mkdir(parents=True, exist_ok=True)

    df = pd.read_csv(data_path)

    payload = build_sequences(df, seq_len=SEQ_LEN)
    action_seq = payload["action_seq"]
    product_seq = payload["product_seq"]
    time_seq = payload["time_seq"]
    targets = payload["targets"]
    action_to_idx = payload["action_to_idx"]
    idx_to_action = payload["idx_to_action"]
    num_products = payload["num_products"]

    indices = np.arange(len(targets))
    train_idx, temp_idx, y_train, y_temp = train_test_split(
        indices,
        targets,
        test_size=0.30,
        random_state=SEED,
        stratify=targets,
    )
    val_idx, test_idx, _, _ = train_test_split(
        temp_idx,
        y_temp,
        test_size=0.50,
        random_state=SEED,
        stratify=y_temp,
    )

    train_ds = SequenceDataset(action_seq[train_idx], product_seq[train_idx], time_seq[train_idx], targets[train_idx])
    val_ds = SequenceDataset(action_seq[val_idx], product_seq[val_idx], time_seq[val_idx], targets[val_idx])
    test_ds = SequenceDataset(action_seq[test_idx], product_seq[test_idx], time_seq[test_idx], targets[test_idx])

    train_loader = DataLoader(train_ds, batch_size=BATCH_SIZE, shuffle=True)
    val_loader = DataLoader(val_ds, batch_size=BATCH_SIZE, shuffle=False)
    test_loader = DataLoader(test_ds, batch_size=BATCH_SIZE, shuffle=False)

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

    model_types = ["RNN", "LSTM", "biLSTM"]
    run_results = []
    histories = {}
    trained_models = {}

    criterion = nn.CrossEntropyLoss()

    for model_name in model_types:
        model = ActionSequenceModel(
            model_type=model_name,
            num_actions=len(action_to_idx),
            num_products=num_products,
            time_dim=time_seq.shape[-1],
        ).to(device)

        optimizer = torch.optim.Adam(model.parameters(), lr=LEARNING_RATE)

        history = {
            "train_loss": [],
            "val_loss": [],
            "train_acc": [],
            "val_acc": [],
        }

        best_state = copy.deepcopy(model.state_dict())
        best_val_f1 = -1.0
        no_improve = 0

        for epoch in range(1, EPOCHS + 1):
            train_loss, train_metrics = run_epoch(
                model,
                train_loader,
                criterion,
                optimizer,
                device,
                train_mode=True,
            )
            val_loss, val_metrics = run_epoch(
                model,
                val_loader,
                criterion,
                optimizer,
                device,
                train_mode=False,
            )

            history["train_loss"].append(train_loss)
            history["val_loss"].append(val_loss)
            history["train_acc"].append(train_metrics["accuracy"])
            history["val_acc"].append(val_metrics["accuracy"])

            if val_metrics["macro_f1"] > best_val_f1 + 1e-6:
                best_val_f1 = val_metrics["macro_f1"]
                best_state = copy.deepcopy(model.state_dict())
                no_improve = 0
            else:
                no_improve += 1

            print(
                f"[{model_name}] Epoch {epoch:02d} | "
                f"train_loss={train_loss:.4f} val_loss={val_loss:.4f} "
                f"train_acc={train_metrics['accuracy']:.4f} val_acc={val_metrics['accuracy']:.4f} "
                f"val_f1={val_metrics['macro_f1']:.4f}"
            )

            if no_improve >= PATIENCE:
                print(f"[{model_name}] Early stopping at epoch {epoch}.")
                break

        model.load_state_dict(best_state)

        test_loss, test_metrics, y_true, y_pred = evaluate_model(model, test_loader, criterion, device)

        run_results.append(
            {
                "model": model_name,
                "test_loss": test_loss,
                **test_metrics,
            }
        )
        histories[model_name] = history
        trained_models[model_name] = {
            "state_dict": copy.deepcopy(model.state_dict()),
            "y_true": y_true,
            "y_pred": y_pred,
        }

        plot_training_curve(history, model_name, output_dir)

    results_df = pd.DataFrame(run_results).sort_values(by=["macro_f1", "accuracy"], ascending=False)
    best_row = results_df.iloc[0]
    best_model_name = best_row["model"]

    plot_metric_comparison(results_df, output_dir)

    best_payload = trained_models[best_model_name]
    plot_confusion(
        best_payload["y_true"],
        best_payload["y_pred"],
        idx_to_action,
        best_model_name,
        output_dir,
    )

    torch.save(
        {
            "model_name": best_model_name,
            "seq_len": SEQ_LEN,
            "num_actions": len(action_to_idx),
            "num_products": num_products,
            "time_dim": time_seq.shape[-1],
            "state_dict": best_payload["state_dict"],
            "action_to_idx": action_to_idx,
            "idx_to_action": idx_to_action,
            "metrics": best_row.to_dict(),
        },
        output_dir / "model_best.pt",
    )

    results_df.to_csv(output_dir / "metrics_summary.csv", index=False)

    with open(output_dir / "selection_summary.txt", "w", encoding="utf-8") as f:
        f.write("Model ranking (by macro_f1 then accuracy):\n")
        for _, row in results_df.iterrows():
            f.write(
                f"- {row['model']}: accuracy={row['accuracy']:.4f}, "
                f"macro_f1={row['macro_f1']:.4f}, "
                f"macro_precision={row['macro_precision']:.4f}, "
                f"macro_recall={row['macro_recall']:.4f}\n"
            )
        f.write(f"\nSelected model_best: {best_model_name}\n")

    print("\n=== Final Test Metrics ===")
    print(results_df.to_string(index=False))
    print(f"\nSelected model_best: {best_model_name}")
    print(f"Artifacts saved to: {output_dir}")


if __name__ == "__main__":
    main()
