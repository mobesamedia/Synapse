"""Dedicated, keyboard-accessible picker. Queries use Anki's serialized worker."""
from .workspace_strings import _
from . import workspace_links as links
from aqt.qt import (QDialog,QVBoxLayout,QHBoxLayout,QLabel,QPushButton,QLineEdit,QComboBox,
                    QListWidget,QListWidgetItem,QPlainTextEdit,QSplitter,QWidget,QDialogButtonBox,QTimer,Qt)

class LinkDialog(QDialog):
    def __init__(self,parent,existing,seed=''):
        super().__init__(parent)
        import aqt
        self.mw=aqt.mw;self.links=links.clean_links(existing);self.items=[];self.statuses={};self.targets={}
        self.closed=False;self.busy=False;self.version=0;self.pending=None;self.result_links=None;self.open_after=None
        self.setWindowTitle(_('Link Card'));self.resize(820,620);self.setMinimumSize(600,460)
        outer=QVBoxLayout(self)
        info=QLabel(_('Link notes or individual cards. Opening a link shows it in Anki’s browser; study progress is unchanged.'))
        info.setWordWrap(True);outer.addWidget(info)
        shortcuts=QHBoxLayout();outer.addLayout(shortcuts)
        current=getattr(getattr(self.mw,'reviewer',None),'card',None) if getattr(self.mw,'state',None)=='review' else None
        self.current_nid=int(current.nid) if current else None;self.current_cid=str(current.id) if current else None
        browser=getattr(aqt.dialogs,'_dialogs',{}).get('Browser',[None,None])[1]
        self.browser_ids=list(browser.selected_notes()) if browser else []
        self.current_btn=QPushButton(_('Current card'));self.current_btn.setEnabled(current is not None)
        self.current_btn.setToolTip(_('Available while reviewing a card.'));shortcuts.addWidget(self.current_btn)
        self.browser_btn=QPushButton(_('Browser selection'));self.browser_btn.setEnabled(bool(self.browser_ids))
        self.browser_btn.setToolTip(_('Select notes or cards in Anki’s browser first.'));shortcuts.addWidget(self.browser_btn);shortcuts.addStretch()
        self.current_btn.clicked.connect(lambda:self.request([self.current_nid],self.current_cid))
        self.browser_btn.clicked.connect(lambda:self.request(self.browser_ids))
        filters=QHBoxLayout();outer.addLayout(filters)
        self.query=QLineEdit();self.query.setPlaceholderText(_('Search notes (Anki search syntax supported)'));self.query.setAccessibleName(_('Search notes'));self.query.setMaxLength(1000)
        self.deck=QComboBox();self.deck.addItem(_('All decks'),'');self.deck.setAccessibleName(_('Deck'));self.deck.setMaximumWidth(210)
        self.tag=QLineEdit();self.tag.setPlaceholderText(_('Filter by tag'));self.tag.setAccessibleName(_('Filter by tag'));self.tag.setMaximumWidth(170);self.tag.setMaxLength(200)
        filters.addWidget(self.query,1);filters.addWidget(self.deck);filters.addWidget(self.tag)
        self.status=QLabel();self.status.setWordWrap(True);outer.addWidget(self.status)
        split=QSplitter();outer.addWidget(split,1)
        self.results=QListWidget();self.results.setAccessibleName(_('Search results'));split.addWidget(self.results)
        right=QWidget();detail=QVBoxLayout(right);split.addWidget(right);split.setSizes([320,430])
        self.preview=QPlainTextEdit();self.preview.setReadOnly(True);self.preview.setAccessibleName(_('Note preview'));detail.addWidget(self.preview,1)
        self.target=QComboBox();self.target.setAccessibleName(_('Link target'));detail.addWidget(self.target)
        self.add=QPushButton(_('Add link'));self.add.setEnabled(False);detail.addWidget(self.add)
        outer.addWidget(QLabel(_('Linked items')))
        row=QHBoxLayout();outer.addLayout(row)
        self.linked=QListWidget();self.linked.setMaximumHeight(100);self.linked.setAccessibleName(_('Linked items'));row.addWidget(self.linked,1)
        actions=QVBoxLayout();row.addLayout(actions)
        self.open=QPushButton(_('Save and open'));self.remove=QPushButton(_('Remove link'));actions.addWidget(self.open);actions.addWidget(self.remove);actions.addStretch()
        buttons=QDialogButtonBox(QDialogButtonBox.StandardButton.Save|QDialogButtonBox.StandardButton.Cancel);outer.addWidget(buttons)
        from .locales import translate_standard_buttons
        translate_standard_buttons(buttons)
        buttons.accepted.connect(self.commit);buttons.rejected.connect(self.reject)
        self.finished.connect(self.finish)
        self.destroyed.connect(lambda:setattr(self,"closed",True))
        self.timer=QTimer(self);self.timer.setSingleShot(True);self.timer.setInterval(300);self.timer.timeout.connect(self.request)
        self.query.textChanged.connect(self.schedule);self.tag.textChanged.connect(self.schedule);self.deck.currentIndexChanged.connect(self.schedule)
        self.query.returnPressed.connect(self.request)
        self.results.currentRowChanged.connect(self.show_preview);self.results.itemDoubleClicked.connect(lambda:self.add_link())
        self.add.clicked.connect(self.add_link);self.remove.clicked.connect(self.remove_link);self.open.clicked.connect(self.open_link)
        self.linked.currentRowChanged.connect(self.link_selection)
        self.linked.itemClicked.connect(self.preview_link)
        self.linked.itemActivated.connect(self.preview_link)
        for button in self.findChildren(QPushButton):button.setAutoDefault(False)
        self.query.setText(seed[:160]);self.refresh_links();self.query.setFocus()
        from aqt.operations import QueryOp
        initial_links=list(self.links)
        QueryOp(parent=self,op=lambda col:([d.name for d in col.decks.all_names_and_ids()],{links.key(link):links.resolve(col,link) for link in initial_links}),success=self.loaded).failure(self.failed).run_in_background()
        self.request()

    def loaded(self,result):
        if self.closed:return
        names,self.targets=result
        self.statuses={key:value is not None for key,value in self.targets.items()}
        self.deck.blockSignals(True)
        for name in names:self.deck.addItem(name,name)
        self.deck.blockSignals(False);self.refresh_links()

    def failed(self,error):
        if not self.closed:self.status.setText(_('Could not search Anki.')+' '+str(error))

    def finish(self,*args):
        self.closed=True;self.timer.stop();self.version+=1

    def schedule(self,*args):
        self.version+=1;self.pending=None;self.results.clear();self.add.setEnabled(False);self.timer.start()

    def request(self,ids=None,preferred=None):
        if self.closed:return
        # clicked/returnPressed can supply a boolean; only explicit lists are IDs.
        if not isinstance(ids,list):ids=None
        self.timer.stop();self.version+=1
        self.pending=(self.version,self.query.text().strip(),self.deck.currentData() or '',self.tag.text().strip(),ids,preferred)
        self.launch()

    def launch(self):
        if self.closed or self.busy or not self.pending:return
        version,text,deck,tag,ids,preferred=self.pending;self.pending=None;self.busy=True
        self.status.setText(_('Searching…'));self.results.clear();self.add.setEnabled(False)
        from aqt.operations import QueryOp
        def done(result=None,error=None):
            self.busy=False
            if self.closed:return
            if version==self.version:
                if error:self.failed(error)
                else:
                    self.items=result['items'];self.preferred=preferred
                    for item in self.items:
                        row=QListWidgetItem(item['title']+'\n'+item['type']+' · '+', '.join(dict.fromkeys(c['deck'] for c in item['cards'])))
                        self.results.addItem(row)
                    self.status.setText(_('Showing the first 60 results. Refine your search.') if result['more'] else (_('Choose a result to preview and link it.') if self.items else _('No matching notes. Try fewer words or use the current card.')))
                    if self.items:self.results.setCurrentRow(0)
            self.launch()
        QueryOp(parent=self,op=lambda col:links.search(col,text,deck,tag,ids),success=lambda r:done(r)).failure(lambda e:done(error=e)).run_in_background()

    def show_preview(self,index):
        self.target.clear();self.preview.clear();self.add.setEnabled(False)
        if index<0 or index>=len(self.items):return
        item=self.items[index]
        self.preview.setPlainText(('\n\n'.join(name+'\n'+value for name,value in item['fields'])+'\n\n'+_('Tags')+': '+', '.join(item['tags']))[:16000])
        self.target.addItem(_('Note · all its cards'),item['note'])
        for card in item['cards']:
            self.target.addItem(_('Card')+' · '+card['name'],card['link'])
            if card['link']['cardId']==getattr(self,'preferred',None):self.target.setCurrentIndex(self.target.count()-1)
        self.add.setEnabled(True)

    def add_link(self):
        link=self.target.currentData()
        if not link:return
        if any(links.key(x)==links.key(link) for x in self.links):
            self.status.setText(_('Already linked.'));return
        if len(self.links)>=links.MAX_LINKS:
            self.status.setText(_('Up to 12 links per object.'));return
        self.links.append(links.clean_link(link));self.statuses[links.key(link)]=True
        self.targets[links.key(link)]={'nid':int(link['noteId']),'cid':int(link['cardId']) if link['kind']=='card' else None}
        self.refresh_links()
        self.linked.setCurrentRow(len(self.links)-1)
        self.status.setText(_('Link added. Save to apply your changes.'))

    def refresh_links(self):
        index=self.linked.currentRow();self.linked.clear()
        for link in self.links:
            label=(_('Card')+' '+str(link['cardOrd']+1) if link['kind']=='card' else _('Note'))+' · '+link['label']
            if self.statuses.get(links.key(link)) is False:label=_('Not found in this collection')+' — '+label
            self.linked.addItem(label)
        if self.links:self.linked.setCurrentRow(max(0,min(index,len(self.links)-1)))
        self.link_selection()

    def link_selection(self,*args):
        i=self.linked.currentRow();valid=0<=i<len(self.links)
        self.remove.setEnabled(valid);self.open.setEnabled(valid and self.statuses.get(links.key(self.links[i])) is not False)

    def preview_link(self,*args):
        index=self.linked.currentRow()
        if index<0:return
        target=self.targets.get(links.key(self.links[index]))
        if target:self.request([target['nid']],str(target.get('cid','')))

    def remove_link(self):
        i=self.linked.currentRow()
        if i>=0:self.links.pop(i);self.refresh_links()

    def open_link(self):
        i=self.linked.currentRow()
        if i>=0:
            self.open_after=self.links[i]
            self.commit()

    def commit(self):
        self.result_links=links.clean_links(self.links);self.accept()
