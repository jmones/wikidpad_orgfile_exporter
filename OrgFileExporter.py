# -*- encoding: utf-8 -*-
##############################################################################
#
#    OrgFileExporter, a python module exporter for exporting WikidPad files to
#    orgfiles.
#    Copyright (c) 2012 Josep Mones Teixidor
#    All rights reserved.
#    
#    
#    Redistribution and use in source and binary forms, with or without modification,
#    are permitted provided that the following conditions are met:
#    
#        * Redistributions of source code must retain the above copyright notice,
#          this list of conditions and the following disclaimer.
#        * Redistributions in binary form must reproduce the above copyright notice,
#          this list of conditions and the following disclaimer in the documentation
#          and/or other materials provided with the distribution.
#        * Neither the name of the <ORGANIZATION> nor the names of its contributors
#          may be used to endorse or promote products derived from this software
#          without specific prior written permission.
#    
#    
#    THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
#    AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
#    IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
#    ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE
#    LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
#    CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
#    SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
#    INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
#    CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
#    ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
#    POSSIBILITY OF SUCH DAMAGE.
#    
##############################################################################

"""
	OrgFileExporter.py
    
    Description:
    This exporter exports WikidPad data to emacs org-mode files (http://orgmode.org).
    
    Features:
    This exporter lacks a lot of features. It's just a quick hack to export some data
    from WikidPad. Feel free to improved. Current supported features:
    * Exporting data to a unique file, each word in a node.
    * It uses pyO
    
    Requirements:
    This exporter needs WikidPad version >= 2.2.
    
    Installation:
    Copy OrgFileExporter.py and PyOrgMode.py files to user_extensions folder (if it doesn't exist just create it as a sibling of extensions).
    
    Usage:
    1.- Select Extra/Export
    2.- Select "Org mode file" in "Export to:" dropdown.
    3.- Select destination file (it will create a single file).
    4.- Adjust all other settings as desired.
    5.- Press OK.
        
    Author:
    Josep Mones Teixidor < jmones at gmail dot com >
"""

from pwiki.StringOps import *
from pwiki.Exporters import AbstractExporter
from pwiki.WikiPyparsing import SyntaxNode
import PyOrgMode
import string
import re
from copy import copy

WIKIDPAD_PLUGIN = (("Exporters", 1),)
LOG = False


def describeExportersV01(mainControl):
    return (OrgFileExporter,)

class OrgFileExporter(AbstractExporter):
    """
    Exports org mode files from WikidPad.
    """
    def __init__(self, mainControl):
        AbstractExporter.__init__(self, mainControl)
        self.wordList = None
        self.exportDest = None
        self.currentContent = []
        self.currentLine = ""
        self.currentIndent = 2
        self.currentWord = ""
        self.niceTitles = {}

    @staticmethod
    def getExportTypes(mainControl, continuousExport=False):
        """
        Return sequence of tuples with the description of export types provided
        by this object. A tuple has the form (<exp. type>,
            <human readable description>)
        All exporters must provide this as a static method (which can be called
        without constructing an object first.

        mainControl -- PersonalWikiFrame object
        continuousExport -- If True, only types with support for continuous export
        are listed.
        """
        if continuousExport:
            # Continuous export not supported
            return ()
        return (
            (u"org_mode", _(u'Org mode file')),
            )

    def getAddOptPanelsForTypes(self, guiparent, exportTypes):
        """
        Construct all necessary GUI panels for additional options
        for the types contained in exportTypes.
        Returns sequence of tuples (<exp. type>, <panel for add. options or None>)

        The panels should use  guiparent  as parent.
        If the same panel is used for multiple export types the function can
        and should include all export types for this panel even if some of
        them weren't requested. Panel objects must not be shared by different
        exporter classes.
        """
        if not u"org_mode" in exportTypes:
            return ()

        return (
            (u"org_mode", None),
            )



    def getExportDestinationWildcards(self, exportType):
        """
        If an export type is intended to go to a file, this function
        returns a (possibly empty) sequence of tuples
        (wildcard description, wildcard filepattern).
        
        If an export type goes to a directory, None is returned
        """
        if exportType == u"org_mode":
            return ((_(u"Org mode file (*.org)"), "*.org"),) 
        return None

    def getAddOptVersion(self):
        """
        Returns the version of the additional options information returned
        by getAddOpt(). If the return value is -1, the version info can't
        be stored between application sessions.
        
        Otherwise, the addopt information can be stored between sessions
        and can later handled back to the export method of the object
        without previously showing the export dialog.
        """
        return -1


    def getAddOpt(self, addoptpanel):
        """
        Reads additional options from panel addoptpanel.
        If getAddOptVersion() > -1, the return value must be a sequence
        of simple string and/or numeric objects. Otherwise, any object
        can be returned (normally the addoptpanel itself)
        """
        return (1,)


    def setAddOpt(self, addOpt, addoptpanel):
        """
        Shows content of addOpt in the addoptpanel (must not be None).
        This function is only called if getAddOptVersion() != -1.
        """
        pass
        
    def flushLine(self, force=False):
        if force or len(self.currentLine) > 0:
            line = (" "*self.currentIndent) + self.currentLine + "\n"
            self.currentContent.append(line.encode("utf-8"))
            self.currentLine = ""
        

    def shouldExport(self, wikiWord, wikiPage=None):
        if not wikiPage:
            try:
                wikiPage = self.wikiDocument.getWikiPage(wikiWord)
            except WikiWordNotFoundException:
                return False

        return strToBool(wikiPage.getAttributes().get("export", ("True",))[-1])

    def getLinkForWikiWord(self, word, default = None):
        relUnAlias = self.wikiDocument.getWikiPageNameForLinkTerm(word)
        if relUnAlias is None:
            return default
        if not self.shouldExport(word):
            return default
            
        return relUnAlias

    def processWikiWord(self, astNodeOrWord, fullContent=None):
        if isinstance(astNodeOrWord, SyntaxNode):
            wikiWord = astNodeOrWord.wikiWord
            titleNode = astNodeOrWord.titleNode
        else:
            wikiWord = astNodeOrWord
            titleNode = None
            
        if titleNode == None:
            title = self.niceTitles.get(wikiWord, None)
            

        link = self.getLinkForWikiWord(wikiWord)

        if link:
            if titleNode is not None:
                self.currentLine += u"[[#%s][" % link
                self.processAst(fullContent, titleNode)
                self.currentLine += u"]]"
            else:
                if title is None: 
                    self.currentLine += u"[[#%s]]" % (link)
                else:
                    self.currentLine += u"[[#%s][%s]]" % (link, title)
        else:
            if titleNode is not None:
                self.processAst(fullContent, titleNode)
            else:
                if isinstance(astNodeOrWord, SyntaxNode):
                    self.currentLine += astNodeOrWord.getString()
                else:
                    self.currentLine += astNodeOrWord

    def processUrlLink(self, fullContent, astNode):
        link = astNode.url
        self.currentLine += u"[[%s][" % link
        if astNode.titleNode is not None:
            self.processAst(fullContent, astNode.titleNode)
        else:
            self.currentLine += astNode.coreNode.getString()
        self.currentLine += "]]"


    def processTable(self, content, astNode):
        """
        Write out content of a table as HTML code.
        
        astNode -- node of type "table"
        """
        self.flushLine()
        table = PyOrgMode.OrgTable.Element()
        table.content = []
 
        for row in astNode.iterFlatByName("tableRow"):
            orgRow = []
            for cell in row.iterFlatByName("tableCell"):
                orgRow.append(cell.getString().encode("utf-8"))
            table.content.append(orgRow)
        self.currentContent.append(table)
        

    def processAst(self, content, pageAst):
        """
        Actual token to org-mode converter. May be called recursively.
        """
        for node in pageAst.iterFlatNamed():
            tname = node.name

            # self.currentLine += "{" + tname + "}"
            
            if tname is None:
                continue            
            elif tname == "plainText":
                if self.removePlainText:
                    # This it the text for the first title in a wikiword,
                    # we use it as a nice title
                    pass
                else:
                    self.currentLine += node.getString()
            elif tname == "lineBreak":
                self.flushLine(True)
            elif tname == "newParagraph":
                self.flushLine()
                self.flushLine(True)
            elif tname == "whitespace":
                self.currentLine += " "
            elif tname == "indentedText":
                self.flushLine()
                self.currentIndent += 2
                self.processAst(content, node)
            elif tname == "orderedList":
                self.flushLine()
                self.processAst(content, node)
            elif tname == "unorderedList":
                self.flushLine()
                self.processAst(content, node)
            elif tname == "romanList":
                self.flushLine()
                self.processAst(content, node)
            elif tname == "alphaList":
                self.flushLine()
                self.processAst(content, node)
            elif tname == "bullet":
                pass
            elif tname == "number":
                pass
            elif tname == "roman":
                pass
            elif tname == "alpha":
                pass
            elif tname == "italics":
                self.currentLine += "/"
                self.processAst(content, node)
                self.currentLine += "/"
            elif tname == "bold":
                self.currentLine += "*"
                self.processAst(content, node)
                self.currentLine += "*"
                
            elif tname == "htmlTag" or tname == "htmlEntity":
                self.currentLine += node.getString()
                #u"[ERROR: We can't process htmlTag or htmlEntity]"
                #print node.getString()

            elif tname == "heading":
                # we ignore the heading, it doesn't fit very well in the
                # exporting model we are using (every wikiword is a node)
                self.flushLine()
                
                # we use the first heading as a friendly title for the node
                if self.itemsProcessed == 0:
                    self.removePlainText = True
                    self.processAst(content, node.contentNode)
                    self.removePlainText = False
                else:
                    self.processAst(content, node.contentNode)

            elif tname == "horizontalLine":
                self.flushLine()
                self.currentLine += "-----"
                self.flushLine()

            elif tname == "preBlock":
                self.flushLine()
                self.currentLine += "#+BEGIN_EXAMPLE"
                self.flushLine()
                for line in string.split(node.findFlatByName("preText").getString(), "\n"):
                    self.currentLine += line
                    self.flushLine()
                self.currentLine += "#+END_EXAMPLE"

            elif tname == "todoEntry":
                # we should create nodes but it's difficult to fit in current "each wiki word is a node scheme"
                self.flushLine()
                self.currentLine += "TODO: %s%s" % (node.key, node.delimiter)
                self.processAst(content, node.valueNode)
                self.flushLine()
            elif tname == "script":
                pass  # Hide scripts
            elif tname == "noExport":
                pass  # Hide no export areas
            elif tname == "anchorDef":
                if self.wordAnchor:
                    self.outAppend('<a name="%s" class="wikidpad"></a>' %
                            (self.wordAnchor + u"#" + node.anchorLink))
                else:
                    self.outAppend('<a name="%s" class="wikidpad"></a>' % node.anchorLink)                
            elif tname == "wikiWord":
                self.processWikiWord(node, content)
            elif tname == "table":
                self.processTable(content, node)
            elif tname == "footnote":
                self.flushLine()
                self.currentLine += u"[ERROR: We can't process footnotes]"
                self.flushLine()
            elif tname == "urlLink":
                self.processUrlLink(content, node)
            elif tname == "stringEnd":
                pass
            else:
                self.flushLine()
                self.currentLine += u'[Unknown parser node with name "%s" found]' % tname
                self.flushLine()
                
            self.itemsProcessed += 1
            

        # if we have a line to flush do it now
        self.flushLine()
                
    def updateNiceTitle(self, content, word, pageAst):
        """
        This gets Nice title
        """
        item = pageAst.iterFlatNamed().next()
        if item.name == 'heading':            
            item = item.contentNode.iterFlatNamed().next()
            if item.name == 'plainText':
                self.niceTitles[word] = item.getString()
                
        
    def export(self, wikiDocument, wordList, exportType, exportDest,
            compatFilenames, addopt, progressHandler):
        """
        Run export operation.
        
        wikiDocument -- WikiDocument object
        wordList -- Sequence of wiki words to export
        exportType -- string tag to identify how to export
        exportDest -- Path to destination directory or file to export to
        compatFilenames -- Should the filenames be encoded to be lowest
                           level compatible
        addopt -- additional options returned by getAddOpt()
        """
        self.wikiDocument = wikiDocument
        self.wordList = wordList
        self.exportDest = exportDest
             
        try:
            org = PyOrgMode.OrgDataStructure()

            # capture nice titles
            for word in self.wordList:
                wikiPage = self.wikiDocument.getWikiPage(word)

                word = wikiPage.getWikiWord()
                content = wikiPage.getLiveText()
                basePageAst = wikiPage.getLivePageAst()
                # set default setting
                self.niceTitles[word] = word
                self.updateNiceTitle(content, word, basePageAst)

            for word in self.wordList:
                wikiPage = self.wikiDocument.getWikiPage(word)

                word = wikiPage.getWikiWord()
                formatDetails = wikiPage.getFormatDetails()
                content = wikiPage.getLiveText()
                basePageAst = wikiPage.getLivePageAst()
                
                self.currentContent = []
                self.currentWord = word
                self.currentLine = ""
                self.itemsProcessed = 0
                self.removePlainText = False
                self.currentIndent = 2
                self.processAst(content, basePageAst)
                

                node = PyOrgMode.OrgNode.Element()
                node.level = 1
                node.heading = self.niceTitles[word].encode("utf-8")
                
                drawer = PyOrgMode.OrgDrawer.Element("PROPERTIES")
                customId = ":CUSTOM_ID: " + word
                drawer.content.append(customId.encode("utf-8"))
                node.content.append(drawer)
                node.content.extend(self.currentContent)

                org.root.append_clean(node)
                org.save_to_file(self.exportDest)    
        except:
            traceback.print_exc()
            




