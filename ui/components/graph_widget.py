import re
import math
import random
import logging
from typing import List, Dict, Any, Optional
from PySide6.QtWidgets import QWidget
from PySide6.QtCore import Qt, QTimer, QPointF
from PySide6.QtGui import QPainter, QColor, QPen, QBrush, QFont, QMouseEvent

logger = logging.getLogger("app")

class Node:
    def __init__(self, paper_id: str, label: str, x: float, y: float):
        self.id = paper_id
        self.label = label
        self.x = x
        self.y = y
        self.vx = 0.0
        self.vy = 0.0
        self.radius = 16.0
        self.hovered = False
        self.dragged = False

class Edge:
    def __init__(self, source: Node, target: Node, weight: float):
        self.source = source
        self.target = target
        self.weight = weight # similarity metric (0.0 to 1.0)

class PaperGraphWidget(QWidget):
    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setMouseTracking(True)
        
        self.nodes: List[Node] = []
        self.edges: List[Edge] = []
        
        self.dragged_node: Optional[Node] = None
        self.hovered_node: Optional[Node] = None
        
        # Physics constants
        self.repulsion = 450.0
        self.spring_k = 0.08
        self.damping = 0.85
        self.ideal_length = 120.0
        
        # Timer for physics iterations (approx 60 fps)
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_physics)
        self.timer.start(16)

    def set_papers(self, papers: List[Dict[str, Any]]) -> None:
        """Clear existing and set up nodes and edges from SQLite metadata list."""
        self.nodes.clear()
        self.edges.clear()
        self.dragged_node = None
        self.hovered_node = None
        
        if not papers:
            self.update()
            return

        # 1. Create Nodes (placed randomly near the center)
        w = self.width() if self.width() > 100 else 400
        h = self.height() if self.height() > 100 else 300
        cx, cy = w / 2, h / 2

        for p in papers:
            title = p.get("title", p.get("name", "Untitled"))
            # Truncate title
            label = title[:35] + "..." if len(title) > 35 else title
            x = cx + random.uniform(-100, 100)
            y = cy + random.uniform(-100, 100)
            self.nodes.append(Node(p["id"], label, x, y))

        # 2. Calculate Jaccard similarity threshold for Edges
        # Create edges if similarity > 0.08
        for i in range(len(papers)):
            for j in range(i + 1, len(papers)):
                sim = self._calculate_similarity(papers[i], papers[j])
                if sim > 0.08:
                    self.edges.append(Edge(self.nodes[i], self.nodes[j], sim))
        
        self.update()

    def _calculate_similarity(self, p1: Dict[str, Any], p2: Dict[str, Any]) -> float:
        """Helper to calculate similarity score of titles and abstracts."""
        text1 = f"{p1.get('title', '')} {p1.get('keywords', '')} {p1.get('abstract', '')}".lower()
        text2 = f"{p2.get('title', '')} {p2.get('keywords', '')} {p2.get('abstract', '')}".lower()
        
        # Extract alphanumeric words
        words1 = set(re.findall(r'\w+', text1))
        words2 = set(re.findall(r'\w+', text2))
        
        # Strip common stopwords
        stopwords = {"the", "a", "an", "and", "of", "in", "to", "for", "on", "with", "is", "that", "this", "by", "as", "from", "at", "it", "we"}
        words1 -= stopwords
        words2 -= stopwords
        
        if not words1 or not words2:
            return 0.0
            
        intersection = words1.intersection(words2)
        union = words1.union(words2)
        return len(intersection) / len(union)

    def update_physics(self) -> None:
        """Standard layout relaxation iteration step."""
        if not self.nodes:
            return

        w = max(self.width(), 200)
        h = max(self.height(), 200)
        cx, cy = w / 2, h / 2

        # 1. Repulsion force between all nodes
        for i, n1 in enumerate(self.nodes):
            for j, n2 in enumerate(self.nodes):
                if i == j:
                    continue
                dx = n1.x - n2.x
                dy = n1.y - n2.y
                dist_sq = dx*dx + dy*dy
                dist = math.sqrt(dist_sq) if dist_sq > 0.01 else 0.1
                
                # Apply repulsion force (Coulomb's Law style)
                if dist < 300:
                    force = self.repulsion / (dist_sq + 10.0)
                    n1.vx += (dx / dist) * force
                    n1.vy += (dy / dist) * force

        # 2. Attraction force along similarity edges (Hooke's Law style)
        for edge in self.edges:
            n1 = edge.source
            n2 = edge.target
            dx = n2.x - n1.x
            dy = n2.y - n1.y
            dist = math.sqrt(dx*dx + dy*dy) if (dx*dx + dy*dy) > 0.01 else 0.1
            
            # Attractive force proportional to connection weight (similarity)
            target_len = self.ideal_length * (1.0 - edge.weight * 0.5)
            force = self.spring_k * (dist - target_len)
            
            # Distribute forces
            fx = (dx / dist) * force
            fy = (dy / dist) * force
            
            n1.vx += fx
            n2.vx -= fx
            n1.vy += fy
            n2.vy -= fy

        # 3. Center gravity (pulls unconnected clusters back to viewport)
        for n in self.nodes:
            n.vx += (cx - n.x) * 0.005
            n.vy += (cy - n.y) * 0.005

        # 4. Integrate velocity into coordinates
        for n in self.nodes:
            if n.dragged:
                continue
            # Apply damping
            n.vx *= self.damping
            n.vy *= self.damping
            n.x += n.vx
            n.y += n.vy
            
            # Constrain to window boundary margins
            margin = 30
            n.x = max(margin, min(w - margin, n.x))
            n.y = max(margin, min(h - margin, n.y))

        self.update()

    # --- QPainter Drawing ---
    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # Determine theme base colors dynamically from background color
        bg_col = self.palette().window().color()
        is_dark = bg_col.lightness() < 128
        
        line_color = QColor("#374151") if is_dark else QColor("#D1D5DB")
        node_color = QColor("#4F46E5") # Primary accent
        hover_node_color = QColor("#10B981") # Success/emerald
        text_color = QColor("#FFFFFF") if is_dark else QColor("#111827")
        
        # 1. Draw Edges
        for edge in self.edges:
            pen = QPen()
            # Thickness proportional to similarity weight
            pen.setWidthF(1.0 + edge.weight * 5.0)
            # Fainter if another node is hovered
            if self.hovered_node and self.hovered_node not in (edge.source, edge.target):
                pen.setColor(QColor(80, 80, 80, 50) if is_dark else QColor(200, 200, 200, 50))
            else:
                pen.setColor(QColor(79, 70, 229, 150) if is_dark else QColor(79, 70, 229, 100))
            
            painter.setPen(pen)
            painter.drawLine(QPointF(edge.source.x, edge.source.y), QPointF(edge.target.x, edge.target.y))

        # 2. Draw Nodes
        for n in self.nodes:
            painter.setPen(Qt.NoPen)
            
            # Determine brush color based on interaction states
            if n.hovered or n.dragged:
                painter.setBrush(QBrush(hover_node_color))
            else:
                # Shade node color slightly by degree of connections
                painter.setBrush(QBrush(node_color))
            
            painter.drawEllipse(QPointF(n.x, n.y), n.radius, n.radius)
            
            # Draw node outline
            outline_pen = QPen(QColor("#FFFFFF"), 2)
            painter.setPen(outline_pen)
            painter.drawEllipse(QPointF(n.x, n.y), n.radius, n.radius)

            # Node Labels (drawn below nodes)
            painter.setPen(QPen(text_color))
            painter.setFont(QFont("Segoe UI", 9, QFont.Bold if n.hovered else QFont.Normal))
            
            # Text box size calculation for centering
            metrics = painter.fontMetrics()
            text_w = metrics.horizontalAdvance(n.label)
            text_h = metrics.height()
            
            # Background panel for labels on dark backgrounds
            if n.hovered:
                label_bg = QColor(17, 24, 39, 230) if is_dark else QColor(255, 255, 255, 230)
                painter.setBrush(QBrush(label_bg))
                painter.setPen(Qt.NoPen)
                painter.drawRoundedRect(n.x - text_w/2 - 6, n.y + n.radius + 4, text_w + 12, text_h + 4, 4, 4)
                painter.setPen(QPen(QColor("#10B981") if is_dark else QColor("#059669")))
                
            painter.drawText(int(n.x - text_w/2), int(n.y + n.radius + 4 + text_h), n.label)

    # --- Mouse Interaction Handling ---
    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        pos = event.position()
        
        # Check node drags
        if self.dragged_node:
            self.dragged_node.x = pos.x()
            self.dragged_node.y = pos.y()
            self.update()
            return
            
        # Check node hovers
        old_hover = self.hovered_node
        self.hovered_node = None
        for n in self.nodes:
            dx = n.x - pos.x()
            dy = n.y - pos.y()
            if (dx*dx + dy*dy) < (n.radius * n.radius):
                n.hovered = True
                self.hovered_node = n
            else:
                n.hovered = False
                
        if self.hovered_node != old_hover:
            self.update()

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.LeftButton:
            pos = event.position()
            for n in self.nodes:
                dx = n.x - pos.x()
                dy = n.y - pos.y()
                if (dx*dx + dy*dy) < (n.radius * n.radius):
                    n.dragged = True
                    self.dragged_node = n
                    break

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.LeftButton and self.dragged_node:
            self.dragged_node.dragged = False
            self.dragged_node = None
            self.update()
