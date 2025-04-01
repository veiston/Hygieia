import collections.abc
from pptx import Presentation

from docx import Document
from docx.shared import Inches

import PyPDF2

import os
import re

from tkinter import Tk     # from tkinter import Tk for Python 3.x
from tkinter.filedialog import askopenfilename


def anyReader():
    Tk().withdraw() # we don't want a full GUI, so keep the root window from appearing
    fullText = ''

    filename = askopenfilename() # show an "Open" dialog box and return the path to the selected file
    document = Document()

    file = filename

    #Identify filetype
    file_extension = os.path.splitext(file)[1]
    print('Filetype: ' + file_extension)

    if file_extension == '.pdf':
            
        #create file object variable
        #opening method will be rb
        pdffileobj = open(filename,'rb')

        #create reader variable that will read the pdffileobj
        pdfreader = PyPDF2.PdfReader(pdffileobj)

        #This will store the number of pages of this pdf file
        pageAmount = len(pdfreader.pages)
        print('Pages to process: ' + str(pageAmount))

        '''
        currentPage = -118
        pageobj = pdfreader.getPage(pageAmount-(pageAmount-currentPage))
        fullText = fullText + pageobj.extractText()
        '''

        for currentPage in range(pageAmount):
            try:
                #create a variable that will select the selected number of pages
                pageobj = pdfreader.pages[pageAmount-(pageAmount-currentPage)]

                #(x+1) because python indentation starts with 0
                #create text variable which will store all text datafrom pdf file
                fullText = fullText + '\n'*2 + str(currentPage + 1) + '\n' + pageobj.extract_text()
                text = fullText
                
            except Exception as e:
                print(str(e) + ' went wrong while processing page ' + str(currentPage+1))

        print('Success!')
        #print('DOCX saved to: ' + filename[0 : len(filename) - (1 + len(str(os.path.basename(file))))] + '\n')

    elif file_extension == '.pptx':
        prs = Presentation(file)
        text_runs = []

        for slide in prs.slides:
            for shape in slide.shapes:
                if not shape.has_text_frame:
                    continue
                for paragraph in shape.text_frame.paragraphs:
                    for run in paragraph.runs:
                        text_runs.append(run.text + ' ')
                    text_runs.append('\n')
            
        text = text_runs

        print(text)

    else:
        text = 'Unsupported filetype'

    return text

if __name__ == "__main__":
    anyReader()