# SPDX-License-Identifier: GPL-3.0-or-later
"""Lazy directory rules; expanding never alters the saved selection."""
from pathlib import Path
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import QTreeWidget,QTreeWidgetItem
import baul_core as core
from localization import tr

class FolderRuleTree(QTreeWidget):
    rulesChanged=pyqtSignal()
    def __init__(self,parent=None):
        super().__init__(parent);self.setHeaderHidden(True);self.setMinimumHeight(150)
        self.rules={};self.roots=[];self.updating=False
        self.itemExpanded.connect(self.load_children);self.itemChanged.connect(self.changed)

    def configure(self,roots,included,excluded=()):
        self.updating=True;self.clear();self.roots=list(roots)
        self.rules={p:True for p in included if self.inside(p)}
        self.rules.update({p:False for p in excluded if self.inside(p)})
        for path in roots:self.add_node(None,path,True)
        self.refresh_states();self.updating=False

    def inside(self,path):
        target=Path(path).resolve()
        return any(target==Path(root).resolve() or Path(root).resolve() in target.parents for root in self.roots)

    def effective(self,path):
        return core.rule_enabled(path,*self.selection())

    def selection(self):
        return ([p for p,v in self.rules.items() if v],[p for p,v in self.rules.items() if not v])

    def add_node(self,parent,path,root=False):
        node=QTreeWidgetItem([path if root else Path(path).name]);node.setData(0,Qt.ItemDataRole.UserRole,path)
        node.setFlags(node.flags()|Qt.ItemFlag.ItemIsUserCheckable)
        node.setChildIndicatorPolicy(QTreeWidgetItem.ChildIndicatorPolicy.ShowIndicator)
        node.setData(0,Qt.ItemDataRole.UserRole+1,False)
        if parent is None:self.addTopLevelItem(node)
        else:parent.addChild(node)
        return node

    def load_children(self,node):
        if node.data(0,Qt.ItemDataRole.UserRole+1):return
        previous=self.updating;self.updating=True;path=Path(node.data(0,Qt.ItemDataRole.UserRole));paths=set()
        try:
            # No recursive walk, no symlink traversal or hidden system folders.
            paths={str(p) for p in path.iterdir() if not p.is_symlink() and p.is_dir() and not p.name.startswith('.') and p.name not in {'$RECYCLE.BIN','System Volume Information'}}
        except OSError:pass
        # Keep disconnected/missing branches that already have explicit rules.
        for rule in self.rules:
            try:
                relative=Path(rule).relative_to(path)
                if relative.parts:paths.add(str(path/relative.parts[0]))
            except ValueError:pass
        for child in sorted(paths,key=lambda p:Path(p).name.casefold()):self.add_node(node,child)
        node.setData(0,Qt.ItemDataRole.UserRole+1,True)
        if not paths:node.setChildIndicatorPolicy(QTreeWidgetItem.ChildIndicatorPolicy.DontShowIndicatorWhenChildless)
        self.refresh_states();self.updating=previous

    def nodes(self):
        pending=[self.topLevelItem(i) for i in range(self.topLevelItemCount())]
        while pending:
            node=pending.pop();yield node
            pending.extend(node.child(i) for i in range(node.childCount()))

    def refresh_states(self):
        previous=self.updating;self.updating=True
        for node in self.nodes():
            path=node.data(0,Qt.ItemDataRole.UserRole);target=Path(path);value=self.effective(path)
            mixed=any(target in Path(p).parents and v!=value for p,v in self.rules.items())
            node.setCheckState(0,Qt.CheckState.PartiallyChecked if mixed else Qt.CheckState.Checked if value else Qt.CheckState.Unchecked)
            node.setToolTip(0,path+'\n'+tr('Selección parcial: despliega para ver las excepciones.' if mixed else 'Incluida; las subcarpetas heredan esta regla.' if value else 'Sin seleccionar; las subcarpetas heredan esta regla.')+('' if target.is_dir() else '\n'+tr('Ubicación no disponible: comprueba su conexión y permisos.')))
        self.updating=previous

    def changed(self,node,column):
        if self.updating:return
        path=node.data(0,Qt.ItemDataRole.UserRole);target=Path(path);value=node.checkState(0)==Qt.CheckState.Checked
        self.rules={p:v for p,v in self.rules.items() if Path(p)!=target and target not in Path(p).parents}
        inherited=self.effective(path)
        if value!=inherited:self.rules[path]=value
        self.refresh_states();self.rulesChanged.emit()
