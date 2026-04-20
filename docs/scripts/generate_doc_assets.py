import math
import random
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[2]
CSV_PATH = PROJECT_ROOT / "data_user500.csv"
OUTPUT_DIR = PROJECT_ROOT / "docs" / "images"


def save_table_image(df: pd.DataFrame, title: str, output_path: Path, font_size: int = 9) -> None:
    rows = len(df)
    cols = len(df.columns)
    fig_h = max(5.0, min(18.0, 1.2 + rows * 0.45))
    fig_w = max(10.0, min(28.0, 2.2 + cols * 2.1))

    fig, ax = plt.subplots(figsize=(fig_w, fig_h))
    ax.axis("off")
    ax.set_title(title, fontsize=13, fontweight="bold", pad=16)

    table = ax.table(
        cellText=df.values,
        colLabels=df.columns,
        cellLoc="center",
        colLoc="center",
        loc="center",
    )
    table.auto_set_font_size(False)
    table.set_fontsize(font_size)
    table.scale(1.0, 1.35)

    for (r, c), cell in table.get_celld().items():
        cell.set_edgecolor("#d6dbe3")
        if r == 0:
            cell.set_text_props(fontweight="bold", color="#1f2937")
            cell.set_facecolor("#eaf2ff")
        elif r % 2 == 0:
            cell.set_facecolor("#f9fbff")
        else:
            cell.set_facecolor("#ffffff")

    fig.tight_layout()
    fig.savefig(output_path, dpi=220, bbox_inches="tight")
    plt.close(fig)


def build_top20_kb_rows(df: pd.DataFrame) -> pd.DataFrame:
    grouped = (
        df.groupby(["user_id", "product_id", "action"])  # action counts
        .size()
        .unstack(fill_value=0)
        .reset_index()
    )

    for col in [
        "view",
        "click",
        "search",
        "add_to_wishlist",
        "add_to_cart",
        "remove_from_cart",
        "checkout",
        "purchase",
    ]:
        if col not in grouped.columns:
            grouped[col] = 0

    grouped["total_interactions"] = grouped[
        [
            "view",
            "click",
            "search",
            "add_to_wishlist",
            "add_to_cart",
            "remove_from_cart",
            "checkout",
            "purchase",
        ]
    ].sum(axis=1)

    grouped = grouped.sort_values(
        by=["total_interactions", "purchase", "checkout", "add_to_cart"],
        ascending=False,
    ).head(20)

    return grouped[
        [
            "user_id",
            "product_id",
            "total_interactions",
            "view",
            "click",
            "search",
            "add_to_wishlist",
            "add_to_cart",
            "remove_from_cart",
            "checkout",
            "purchase",
        ]
    ]


def save_kb_graph_image(df: pd.DataFrame, output_path: Path) -> None:
    try:
        import networkx as nx
    except ImportError:
        # Fallback diagram if networkx is not installed.
        fig, ax = plt.subplots(figsize=(16, 10))
        ax.axis("off")
        ax.set_title("KB_Graph Multi-Layer (Fallback)", fontsize=16, fontweight="bold", pad=20)

        layers = {
            "Users": (0.12, [f"U{i:04d}" for i in range(1, 9)]),
            "Actions": (0.38, ["view", "click", "search", "wishlist", "cart", "checkout", "purchase"]),
            "Products": (0.68, [f"P{i:04d}" for i in range(1, 15)]),
            "TimeSlots": (0.9, [f"H{h:02d}" for h in [8, 10, 14, 16, 20, 22]]),
        }

        node_pos = {}
        node_color = {
            "Users": "#4f7df3",
            "Actions": "#ff8a3d",
            "Products": "#13a57b",
            "TimeSlots": "#8b5cf6",
        }

        for layer_name, (x, nodes) in layers.items():
            ys = [0.1 + i * (0.8 / max(1, len(nodes) - 1)) for i in range(len(nodes))]
            for node, y in zip(nodes, ys):
                node_pos[node] = (x, y)
                ax.scatter(x, y, s=250, c=node_color[layer_name], alpha=0.9, edgecolors="white", linewidths=1.2)
                ax.text(x, y, node, color="white", fontsize=8, ha="center", va="center")

        edges = []
        for i in range(1, 9):
            u = f"U{i:04d}"
            edges.append((u, "view"))
            edges.append((u, "click"))
            edges.append((u, "search"))

        for a in ["view", "click", "search", "wishlist", "cart", "checkout", "purchase"]:
            for p in [f"P{i:04d}" for i in range(1, 10)]:
                if (hash(a + p) % 3) == 0:
                    edges.append((a, p))

        for p in [f"P{i:04d}" for i in range(1, 15)]:
            for h in ["H08", "H10", "H14", "H16", "H20", "H22"]:
                if (hash(p + h) % 5) == 0:
                    edges.append((p, h))

        for src, dst in edges:
            if src in node_pos and dst in node_pos:
                x1, y1 = node_pos[src]
                x2, y2 = node_pos[dst]
                ax.plot([x1, x2], [y1, y2], color="#cbd5e1", alpha=0.35, linewidth=0.8)

        fig.tight_layout()
        fig.savefig(output_path, dpi=240, bbox_inches="tight")
        plt.close(fig)
        return

    # High-value complex graph with explicit multi-layer layout.
    g = nx.MultiDiGraph()

    df = df.copy()
    df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True, errors="coerce")
    df = df.dropna(subset=["timestamp"])

    top_users = df["user_id"].value_counts().head(80).index.tolist()
    top_products = df["product_id"].value_counts().head(220).index.tolist()
    action_nodes = sorted(df["action"].unique().tolist())

    df_sub = df[df["user_id"].isin(top_users) & df["product_id"].isin(top_products)].copy()
    df_sub["hour_slot"] = "H" + df_sub["timestamp"].dt.hour.astype(str).str.zfill(2)
    top_slots = df_sub["hour_slot"].value_counts().head(24).index.tolist()
    df_sub = df_sub[df_sub["hour_slot"].isin(top_slots)]

    for u in top_users:
        g.add_node(u, group="user")
    for a in action_nodes:
        g.add_node(a, group="action")
    for p in top_products:
        g.add_node(p, group="product")
    for t in top_slots:
        g.add_node(t, group="timeslot")

    transitions = df_sub.sort_values(["user_id", "timestamp"]).copy()
    transitions["next_action"] = transitions.groupby("user_id")["action"].shift(-1)
    transitions = transitions.dropna(subset=["next_action"])
    aa = (
        transitions.groupby(["action", "next_action"]).size().reset_index(name="w")
        .sort_values("w", ascending=False)
    )

    def layered_pos(nodes, x, y_start=0.06, y_end=0.94):
        if not nodes:
            return {}
        if len(nodes) == 1:
            return {nodes[0]: (x, (y_start + y_end) / 2)}
        step = (y_end - y_start) / (len(nodes) - 1)
        return {node: (x, y_start + idx * step) for idx, node in enumerate(nodes)}

    pos = {}
    pos.update(layered_pos(top_users, 0.08, y_start=0.03, y_end=0.97))
    pos.update(layered_pos(action_nodes, 0.34, y_start=0.12, y_end=0.88))
    pos.update(layered_pos(top_products, 0.64, y_start=0.03, y_end=0.97))
    pos.update(layered_pos(top_slots, 0.91, y_start=0.03, y_end=0.97))

    fig, ax = plt.subplots(figsize=(24, 14))
    ax.set_facecolor("#f4f8ff")
    fig.patch.set_facecolor("#f4f8ff")
    ax.axis("off")

    group_conf = {
        "user": {"color": "#3b82f6", "size": 62, "alpha": 0.88},
        "action": {"color": "#f59e0b", "size": 930, "alpha": 0.98},
        "product": {"color": "#10b981", "size": 40, "alpha": 0.88},
        "timeslot": {"color": "#8b5cf6", "size": 120, "alpha": 0.95},
    }

    for group, conf in group_conf.items():
        nodes = [n for n, d in g.nodes(data=True) if d.get("group") == group]
        if not nodes:
            continue
        nx.draw_networkx_nodes(
            g,
            pos,
            nodelist=nodes,
            node_color=conf["color"],
            node_size=conf["size"],
            alpha=conf["alpha"],
            linewidths=0.8,
            edgecolors="#ffffff",
            ax=ax,
        )

    # Draw event trajectories to create high-density visual evidence.
    trajectories = df_sub[["user_id", "action", "product_id", "hour_slot"]].dropna()
    for _, row in trajectories.iterrows():
        u = row["user_id"]
        a = row["action"]
        p = row["product_id"]
        t = row["hour_slot"]
        if u not in pos or a not in pos or p not in pos or t not in pos:
            continue

        x1, y1 = pos[u]
        x2, y2 = pos[a]
        x3, y3 = pos[p]
        x4, y4 = pos[t]

        ax.plot([x1, x2], [y1, y2], color="#fb923c", alpha=0.12, lw=0.7)
        ax.plot([x2, x3], [y2, y3], color="#3b82f6", alpha=0.10, lw=0.7)
        ax.plot([x3, x4], [y3, y4], color="#8b5cf6", alpha=0.12, lw=0.7)

    # Overlay NEXT_ACTION links with stronger emphasis.
    for _, row in aa.iterrows():
        a1 = row["action"]
        a2 = row["next_action"]
        if a1 not in pos or a2 not in pos:
            continue
        x1, y1 = pos[a1]
        x2, y2 = pos[a2]
        lw = max(1.0, float(row["w"]) * 0.40)
        ax.plot([x1, x2], [y1, y2], color="#e11d48", alpha=0.70, lw=lw)

    # Label only strategic nodes to keep readability.
    label_nodes = set(action_nodes)
    label_nodes.update(top_slots[:12])
    nx.draw_networkx_labels(
        g,
        pos,
        labels={n: n for n in label_nodes if n in pos},
        font_size=8,
        font_weight="bold",
        font_color="#111827",
        ax=ax,
    )

    ax.axvline(x=0.20, ymin=0.04, ymax=0.96, color="#cfd8e6", lw=1.0, alpha=0.55)
    ax.axvline(x=0.49, ymin=0.04, ymax=0.96, color="#cfd8e6", lw=1.0, alpha=0.55)
    ax.axvline(x=0.78, ymin=0.04, ymax=0.96, color="#cfd8e6", lw=1.0, alpha=0.55)

    ax.text(0.08, 0.97, "Users", fontsize=12, fontweight="bold", color="#1e3a8a", transform=ax.transAxes)
    ax.text(0.33, 0.97, "Actions", fontsize=12, fontweight="bold", color="#92400e", transform=ax.transAxes)
    ax.text(0.63, 0.97, "Products", fontsize=12, fontweight="bold", color="#065f46", transform=ax.transAxes)
    ax.text(0.89, 0.97, "TimeSlots", fontsize=12, fontweight="bold", color="#5b21b6", transform=ax.transAxes)

    ax.set_title(
        "KB_Graph: High-Density Multi-Layer Graph (User-Action-Product-Time)",
        fontsize=19,
        fontweight="bold",
        pad=14,
        color="#0f172a",
    )

    legend_handles = [
        plt.Line2D([0], [0], marker="o", color="w", label="User", markerfacecolor="#3b82f6", markersize=9),
        plt.Line2D([0], [0], marker="o", color="w", label="Action", markerfacecolor="#f59e0b", markersize=11),
        plt.Line2D([0], [0], marker="o", color="w", label="Product", markerfacecolor="#10b981", markersize=9),
        plt.Line2D([0], [0], marker="o", color="w", label="TimeSlot", markerfacecolor="#8b5cf6", markersize=10),
        plt.Line2D([0], [0], color="#fb923c", lw=2, label="User -> Action"),
        plt.Line2D([0], [0], color="#3b82f6", lw=2, label="Action -> Product"),
        plt.Line2D([0], [0], color="#8b5cf6", lw=2, label="Product -> TimeSlot"),
        plt.Line2D([0], [0], color="#f43f5e", lw=2, label="NEXT_ACTION"),
    ]
    ax.legend(handles=legend_handles, loc="lower left", frameon=True, framealpha=0.95, fontsize=10)

    fig.tight_layout()
    fig.savefig(output_path, dpi=280, bbox_inches="tight")
    plt.close(fig)


def save_rag_pipeline_image(output_path: Path) -> None:
    fig, ax = plt.subplots(figsize=(18, 10))
    ax.axis("off")
    ax.set_xlim(0, 18)
    ax.set_ylim(0, 10)
    ax.set_facecolor("#f8fafc")
    fig.patch.set_facecolor("#f8fafc")

    def box(x, y, w, h, text, face, edge="#1f2937"):
        rect = plt.Rectangle((x, y), w, h, facecolor=face, edgecolor=edge, linewidth=1.5, zorder=2)
        ax.add_patch(rect)
        ax.text(x + w / 2, y + h / 2, text, ha="center", va="center", fontsize=10, color="#111827", fontweight="bold")

    def arrow(x1, y1, x2, y2, color="#334155"):
        ax.annotate(
            "",
            xy=(x2, y2),
            xytext=(x1, y1),
            arrowprops=dict(arrowstyle="->", lw=1.7, color=color),
            zorder=3,
        )

    box(0.8, 7.6, 2.7, 1.2, "User Query", "#dbeafe")
    box(4.0, 7.6, 3.0, 1.2, "API Gateway\n/chat/advice/", "#ede9fe")
    box(7.5, 7.6, 3.2, 1.2, "AISERVICE\nGraphRAGChatView", "#dcfce7")
    box(11.2, 7.6, 2.8, 1.2, "Intent Router", "#fef3c7")
    box(14.5, 7.6, 2.7, 1.2, "Answer + JSON", "#d1fae5")

    box(11.0, 5.6, 3.2, 1.2, "KBGraphRAG.ask", "#ffedd5")
    box(14.8, 5.6, 2.2, 1.2, "Neo4j\nKB_Graph", "#fee2e2")

    box(7.5, 3.7, 3.1, 1.1, "_fetch_recommendations", "#cffafe")
    box(11.1, 3.7, 3.0, 1.1, "_fetch_semantic_products\n(fallback)", "#e0e7ff")
    box(14.6, 3.7, 2.7, 1.1, "products +\nrecommendations", "#fef9c3")

    box(7.2, 1.8, 4.2, 1.1, "Citations + graph_context + confidence", "#e2e8f0")
    box(12.0, 1.8, 5.3, 1.1, "Custom Concierge UI\n(search/cart/chat panel)", "#fde68a")

    arrow(3.5, 8.2, 4.0, 8.2)
    arrow(7.0, 8.2, 7.5, 8.2)
    arrow(10.7, 8.2, 11.2, 8.2)
    arrow(14.0, 8.2, 14.5, 8.2)

    arrow(12.6, 7.6, 12.6, 6.8)
    arrow(14.2, 6.2, 14.8, 6.2)
    arrow(14.8, 7.0, 13.0, 7.6)

    arrow(9.1, 7.6, 9.1, 4.8)
    arrow(10.4, 7.6, 12.0, 4.8)
    arrow(14.1, 4.25, 14.6, 4.25)

    arrow(10.0, 3.7, 10.0, 2.9)
    arrow(14.6, 2.35, 12.0, 2.35)

    ax.text(
        9.0,
        9.5,
        "Cau 2d - Graph RAG Chat Integration Pipeline",
        ha="center",
        va="center",
        fontsize=18,
        fontweight="bold",
        color="#0f172a",
    )

    ax.text(
        9.0,
        0.7,
        "Flow: Query -> AISERVICE -> KB_Graph retrieve/fallback -> grounded answer -> custom e-commerce chat UI",
        ha="center",
        va="center",
        fontsize=10,
        color="#334155",
    )

    fig.tight_layout()
    fig.savefig(output_path, dpi=260, bbox_inches="tight")
    plt.close(fig)


def build_product_category_rows(df: pd.DataFrame, limit: int = 20) -> pd.DataFrame:
    categories = ["books", "fashion", "electronics", "beauty", "sports", "food", "toys"]
    products = df["product_id"].value_counts().index.tolist()
    rows = []
    for pid in products[:limit]:
        try:
            pid_num = int(str(pid).replace("P", ""))
        except ValueError:
            pid_num = abs(hash(pid))
        category = categories[pid_num % len(categories)]
        rows.append({"p": str(pid), "relationship": "BELONGS_TO", "c": category})
    return pd.DataFrame(rows)


def save_scene_full_structure(df: pd.DataFrame, output_path: Path) -> None:
    try:
        import networkx as nx
    except ImportError:
        fig, ax = plt.subplots(figsize=(16, 9))
        ax.axis("off")
        ax.set_facecolor("#0b1324")
        fig.patch.set_facecolor("#0b1324")
        ax.text(
            0.5,
            0.5,
            "Scene Toan Bo Cau Truc\n(Can cai dat networkx de render do thi day du)",
            color="white",
            ha="center",
            va="center",
            fontsize=18,
            fontweight="bold",
            transform=ax.transAxes,
        )
        fig.tight_layout()
        fig.savefig(output_path, dpi=240, bbox_inches="tight")
        plt.close(fig)
        return

    rng = random.Random(42)

    work = df.copy()
    work["timestamp"] = pd.to_datetime(work["timestamp"], utc=True, errors="coerce")
    work = work.dropna(subset=["timestamp"])
    work = work.sort_values(["user_id", "timestamp"]).head(1800)

    users = work["user_id"].value_counts().head(140).index.tolist()
    products = work["product_id"].value_counts().head(280).index.tolist()
    actions = sorted(work["action"].unique().tolist())
    slots = sorted({f"H{h:02d}" for h in work["timestamp"].dt.hour.tolist()})[:24]
    categories = ["books", "fashion", "electronics", "beauty", "sports", "food", "toys"]

    work = work[work["user_id"].isin(users) & work["product_id"].isin(products)].copy()
    work["slot"] = "H" + work["timestamp"].dt.hour.astype(str).str.zfill(2)

    product_to_cat = {}
    for pid in products:
        try:
            pid_num = int(str(pid).replace("P", ""))
        except ValueError:
            pid_num = abs(hash(pid))
        product_to_cat[pid] = categories[pid_num % len(categories)]

    g = nx.Graph()
    for u in users:
        g.add_node(u, group="user")
    for p in products:
        g.add_node(p, group="product")
    for a in actions:
        g.add_node(a, group="action")
    for s in slots:
        g.add_node(s, group="slot")
    for c in categories:
        g.add_node(c, group="category")

    for _, row in work.iterrows():
        u = row["user_id"]
        p = row["product_id"]
        a = row["action"]
        s = row["slot"]
        c = product_to_cat.get(p)
        if s in slots:
            g.add_edge(u, s)
        g.add_edge(u, a)
        g.add_edge(a, p)
        if c:
            g.add_edge(p, c)

    trans = work[["user_id", "action", "timestamp"]].sort_values(["user_id", "timestamp"])
    trans["next_action"] = trans.groupby("user_id")["action"].shift(-1)
    trans = trans.dropna(subset=["next_action"])
    for _, row in trans.iterrows():
        g.add_edge(row["action"], row["next_action"])

    pos = nx.spring_layout(g, seed=42, k=0.20, iterations=150)

    fig, ax = plt.subplots(figsize=(21, 12))
    ax.set_facecolor("#0b1324")
    fig.patch.set_facecolor("#0b1324")
    ax.axis("off")

    nx.draw_networkx_edges(g, pos, ax=ax, edge_color="#9fb4d8", alpha=0.12, width=0.5)

    group_style = {
        "user": {"color": "#8ec5ff", "size": 13},
        "product": {"color": "#b69cff", "size": 10},
        "action": {"color": "#ffea70", "size": 120},
        "slot": {"color": "#ff8f70", "size": 32},
        "category": {"color": "#ff4d6d", "size": 180},
    }

    for group, style in group_style.items():
        nodes = [n for n, d in g.nodes(data=True) if d.get("group") == group]
        if not nodes:
            continue
        nx.draw_networkx_nodes(
            g,
            pos,
            nodelist=nodes,
            node_color=style["color"],
            node_size=style["size"],
            alpha=0.95 if group in {"action", "category"} else 0.85,
            linewidths=0.35,
            edgecolors="#ffffff",
            ax=ax,
        )

    labels = {n: n for n in categories + actions}
    nx.draw_networkx_labels(g, pos, labels=labels, font_size=8, font_color="#f8fafc", font_weight="bold", ax=ax)

    ax.set_title(
        "Scene Toan Bo Cau Truc: User-Action-Product-Category-TimeSlot",
        color="#f8fafc",
        fontsize=18,
        fontweight="bold",
        pad=16,
    )

    legend_handles = [
        plt.Line2D([0], [0], marker="o", color="w", label="User", markerfacecolor="#8ec5ff", markersize=7),
        plt.Line2D([0], [0], marker="o", color="w", label="Product", markerfacecolor="#b69cff", markersize=7),
        plt.Line2D([0], [0], marker="o", color="w", label="Action", markerfacecolor="#ffea70", markersize=10),
        plt.Line2D([0], [0], marker="o", color="w", label="TimeSlot", markerfacecolor="#ff8f70", markersize=8),
        plt.Line2D([0], [0], marker="o", color="w", label="Category", markerfacecolor="#ff4d6d", markersize=10),
    ]
    ax.legend(handles=legend_handles, loc="lower left", frameon=True, framealpha=0.2, fontsize=10, labelcolor="#f8fafc")

    fig.tight_layout()
    fig.savefig(output_path, dpi=260, bbox_inches="tight")
    plt.close(fig)


def save_scene_user_centric(df: pd.DataFrame, output_path: Path) -> None:
    try:
        import networkx as nx
    except ImportError:
        fig, ax = plt.subplots(figsize=(12, 8))
        ax.axis("off")
        ax.text(0.5, 0.5, "User-centric scene (networkx missing)", ha="center", va="center", fontsize=18)
        fig.tight_layout()
        fig.savefig(output_path, dpi=220, bbox_inches="tight")
        plt.close(fig)
        return

    work = df.copy()
    work["timestamp"] = pd.to_datetime(work["timestamp"], utc=True, errors="coerce")
    work = work.dropna(subset=["timestamp"])

    user = work["user_id"].value_counts().idxmax()
    user_df = work[work["user_id"] == user].copy()

    top_products = user_df["product_id"].value_counts().head(8).index.tolist()
    actions = sorted(user_df["action"].unique().tolist())
    top_slots = ("H" + user_df["timestamp"].dt.hour.astype(str).str.zfill(2)).value_counts().head(4).index.tolist()

    categories = ["books", "fashion", "electronics", "beauty", "sports", "food", "toys"]
    product_to_cat = {}
    for pid in top_products:
        try:
            pid_num = int(str(pid).replace("P", ""))
        except ValueError:
            pid_num = abs(hash(pid))
        product_to_cat[pid] = categories[pid_num % len(categories)]

    g = nx.DiGraph()
    center = f"{user}"
    g.add_node(center, group="user")

    for a in actions:
        g.add_node(a, group="action")
        g.add_edge(center, a)

    for idx, p in enumerate(top_products):
        g.add_node(p, group="product")
        g.add_edge(actions[idx % max(1, len(actions))], p)
        c = product_to_cat[p]
        g.add_node(c, group="category")
        g.add_edge(p, c)

    for s in top_slots:
        g.add_node(s, group="slot")
        g.add_edge(center, s)

    pos = {center: (0.0, 0.0)}

    def circular(nodes, radius, phase=0.0):
        if not nodes:
            return {}
        out = {}
        n = len(nodes)
        for i, node in enumerate(nodes):
            theta = phase + (2 * math.pi * i / n)
            out[node] = (radius * math.cos(theta), radius * math.sin(theta))
        return out

    pos.update(circular(actions, 1.25, phase=0.2))
    pos.update(circular(top_products, 2.2, phase=0.5))
    unique_cats = sorted(set(product_to_cat.values()))
    pos.update(circular(unique_cats, 3.0, phase=1.0))
    pos.update(circular(top_slots, 3.6, phase=0.0))

    fig, ax = plt.subplots(figsize=(13, 9))
    ax.set_facecolor("#0f172a")
    fig.patch.set_facecolor("#0f172a")
    ax.axis("off")

    nx.draw_networkx_edges(g, pos, ax=ax, edge_color="#c7d2fe", alpha=0.55, arrows=True, arrowsize=12, width=1.0)

    styles = {
        "user": ("#ef4444", 780),
        "action": ("#93c5fd", 560),
        "product": ("#a7f3d0", 520),
        "category": ("#fde68a", 700),
        "slot": ("#c4b5fd", 600),
    }
    for group, (color, size) in styles.items():
        nodes = [n for n, d in g.nodes(data=True) if d.get("group") == group]
        if nodes:
            nx.draw_networkx_nodes(g, pos, nodelist=nodes, node_color=color, node_size=size, alpha=0.95, edgecolors="#111827", ax=ax)

    labels = {n: n for n in g.nodes()}
    nx.draw_networkx_labels(g, pos, labels=labels, font_size=8, font_weight="bold", font_color="#f8fafc", ax=ax)

    ax.set_title("Scene User-Centric", color="#f8fafc", fontsize=18, fontweight="bold", pad=12)
    fig.tight_layout()
    fig.savefig(output_path, dpi=260, bbox_inches="tight")
    plt.close(fig)


def save_graph_20_rows_image(rows_df: pd.DataFrame, output_path: Path) -> None:
    display_df = rows_df.copy().head(20)
    display_df.insert(0, "#", [str(i) for i in range(1, len(display_df) + 1)])

    fig, ax = plt.subplots(figsize=(12, 9))
    fig.patch.set_facecolor("#111827")
    ax.set_facecolor("#111827")
    ax.axis("off")

    ax.text(
        0.02,
        0.97,
        "20 dong Graph (Neo4j style)",
        color="#f9fafb",
        fontsize=15,
        fontweight="bold",
        va="top",
        transform=ax.transAxes,
    )

    table = ax.table(
        cellText=display_df.values,
        colLabels=display_df.columns,
        cellLoc="left",
        colLoc="left",
        bbox=[0.02, 0.03, 0.96, 0.89],
    )
    table.auto_set_font_size(False)
    table.set_fontsize(10)
    table.scale(1.0, 1.3)

    for (r, c), cell in table.get_celld().items():
        cell.set_edgecolor("#374151")
        if r == 0:
            cell.set_facecolor("#1f2937")
            cell.get_text().set_color("#f9fafb")
            cell.get_text().set_fontweight("bold")
        else:
            cell.set_facecolor("#111827" if r % 2 else "#0b1220")
            cell.get_text().set_color("#d1d5db")

    fig.tight_layout()
    fig.savefig(output_path, dpi=260, bbox_inches="tight")
    plt.close(fig)


def save_neo4j_query_scene(rows_df: pd.DataFrame, output_path: Path) -> None:
    rows = rows_df.head(10).to_dict("records")

    fig, ax = plt.subplots(figsize=(16, 9))
    fig.patch.set_facecolor("#0b1020")
    ax.set_facecolor("#0b1020")
    ax.axis("off")
    ax.set_xlim(0, 16)
    ax.set_ylim(0, 9)

    # Left information panel
    ax.add_patch(plt.Rectangle((0.3, 0.4), 3.8, 8.1, facecolor="#121a2f", edgecolor="#334155", linewidth=1.2))
    ax.text(0.55, 8.1, "Database Information", color="#f8fafc", fontsize=11, fontweight="bold")
    ax.text(0.55, 7.6, "Nodes: User, Product, Action, Category", color="#93c5fd", fontsize=9)
    ax.text(0.55, 7.25, "Relationships: PERFORMED, BELONGS_TO", color="#c4b5fd", fontsize=9)
    ax.text(0.55, 6.9, "Property keys: user_id, product_id, category", color="#a7f3d0", fontsize=9)

    # Query editor panel
    ax.add_patch(plt.Rectangle((4.4, 5.2), 11.1, 3.3, facecolor="#0f172a", edgecolor="#334155", linewidth=1.2))
    ax.text(4.7, 8.1, "Truy van Neo4j", color="#f8fafc", fontsize=12, fontweight="bold")

    query = [
        "MATCH (p:Product)-[r:BELONGS_TO]->(c:Category)",
        "WHERE p.product_id IS NOT NULL",
        "RETURN p.product_id AS product, type(r) AS relationship, c.name AS category",
        "LIMIT 20;",
    ]
    y = 7.6
    for line in query:
        ax.text(4.7, y, line, color="#f9fafb", fontsize=10, family="monospace")
        y -= 0.55

    # Result panel
    ax.add_patch(plt.Rectangle((4.4, 0.4), 11.1, 4.5, facecolor="#111827", edgecolor="#334155", linewidth=1.2))
    ax.text(4.7, 4.55, "Graph Result (sample)", color="#f8fafc", fontsize=11, fontweight="bold")

    y = 4.1
    for i, row in enumerate(rows, 1):
        ax.text(
            4.7,
            y,
            f"{i:>2}. {row['p']}  -[{row['relationship']}]->  {row['c']}",
            color="#d1d5db",
            fontsize=9.5,
            family="monospace",
        )
        y -= 0.34
        if y < 0.7:
            break

    fig.tight_layout()
    fig.savefig(output_path, dpi=260, bbox_inches="tight")
    plt.close(fig)


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    df = pd.read_csv(CSV_PATH)

    data_top20 = df.head(20).copy()
    save_table_image(
        data_top20,
        "Top 20 rows from data_user500.csv",
        OUTPUT_DIR / "data_user500_top20.png",
        font_size=8,
    )

    kb_top20 = build_top20_kb_rows(df)
    save_table_image(
        kb_top20,
        "KB_Graph Interaction Summary - Top 20 user-product rows",
        OUTPUT_DIR / "kb_graph_top20_rows.png",
        font_size=8,
    )

    save_kb_graph_image(df, OUTPUT_DIR / "kb_graph_complex.png")
    save_rag_pipeline_image(OUTPUT_DIR / "rag_pipeline_2d.png")

    graph_rows = build_product_category_rows(df, limit=20)
    save_scene_full_structure(df, OUTPUT_DIR / "scene_full_structure.png")
    save_scene_user_centric(df, OUTPUT_DIR / "scene_user_centric.png")
    save_graph_20_rows_image(graph_rows, OUTPUT_DIR / "scene_graph_20_rows.png")
    save_neo4j_query_scene(graph_rows, OUTPUT_DIR / "scene_neo4j_query.png")

    print("Generated images:")
    for p in sorted(OUTPUT_DIR.glob("*.png")):
        print(f"- {p}")


if __name__ == "__main__":
    main()
