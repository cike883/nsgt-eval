#!/usr/bin/python

import sys,os,os.path,string,re,codecs
from subprocess import *

from pygments import highlight
from pygments.lexers import MatlabLexer
from pygments.formatters import HtmlFormatter

import docutils.core

class Mat2docError(Exception):
    def __init__(self, value):
        self.value = value
    def __str__(self):
        return repr(self.value)

def myexec(s):
    print 'Executing: '+s

    p=Popen(s,shell=True,stdout=PIPE,stderr=PIPE,close_fds=True)
    sts = os.waitpid(p.pid, 0)
    buf=p.stdout.readlines()
    if len(buf)>0:
        print '   STDOUT:'
        for line in buf:
            print line

    buf=p.stderr.readlines()
    if len(buf)>0:
        print '   STDERR:'
        for line in buf:
            print line

def saferead(filename):
    f=codecs.open(filename,'r',encoding="utf-8")
    buf=unicode(f.read())
    f.close()

    return buf

def safewrite(filename,buf):

    #f.write(unicode(line+'\n','latin-1'))
            
    f=codecs.open(filename,'w',encoding="utf-8")
    #f=file(filename,'r')
    f.write(buf)
    f.close()

def safereadlines(filename):
    buf=saferead(filename)
    linebuf=buf.split('\n')
    #while(len(linebuf[-1])==0):
    #    linebuf.pop()

    return linebuf
    
def safewritelines(filename,buf):
    safewrite(filename,'\n'.join(buf)+'\n')


def call_rst(instring,outtype):
    # NOTE TO SELF: The name of the commandline option is
    # math-output, but the option set here math_output. All
    # options behave similarly.

    # Substitutions for making restructuredtext easier
    instring = re.sub(r"\\\\",r"\\\\\\\\",instring)

    if outtype=='php' or outtype=='html':
        args = {
            'math_output' : 'MathJax',
            'initial_header_level' : 2
            }
    else:
        args = {
            'initial_header_level' : 3,
            }
    
    # Look up the correct writer name
    writernames={}
    writernames['php']='html'
    writernames['html']='html'
    writernames['tex']='latex2e'

    #instring+='CLOSETHEDAMMTHINGIE.\n'

    # Call rst2html or similar
    buf=docutils.core.publish_string(instring,writer_name=writernames[outtype],
                                     settings=None, settings_overrides=args)

    return buf

def call_bibtex2html(reflist,conf):
    outname=conf.g.tmpdir+'reflist'

    safewritelines(outname,reflist)
    #f=file(outname,'w')
    #f.write(' '.join(reflist))
    #f.close()

    s='bibtex2html --warn-error --no-abstract --no-keys --no-keywords --nodoc --nobibsource --no-header --citefile '+outname+' -s '+conf.t.bibstyle+' --output '+outname+' '+conf.g.bibfile+'.bib'

    output=check_output(s,shell=True,stderr=PIPE)

    if 'Warning' in output:
        print output
        print 'STOPPING MAT2DOC: bibtex key missing in bibfile'
        sys.exit()

    buf=saferead(outname+'.html')

    # Strip the annoying footer
    ii=buf.find('<hr>')
    buf=buf[:ii]+'\n'

    return buf.split('\n')


def rst_postprocess(instr,outtype):


    if outtype=='tex':
        instr = re.sub("\\\\section\*{","\\subsubsection*{",instr)
        instr = re.sub("\\\\phantomsection","",instr)
        instr = re.sub("\\\\addcontentsline.*\n","",instr)
        instr = re.sub("\\\\newcounter{listcnt0}","\\\setcounter{listcnt0}{0}",instr)


    buf = instr.split('\n')

    # php specific transformations
    if outtype=='php' or outtype=='html':
        # Transform <em> into <var>
        #buf=  re.sub('<em>','<var>',buf)
        #buf=  re.sub('</em>','</var>',buf)
        
        # Adjust the indexing to remove the <body> and <div document> tags.
        buf=buf[buf.index('<body>')+2:buf.index('</body>')-1]

    if outtype=='tex':
        
        # Adjust the indexing to only include the relevant parts
        buf=buf[buf.index('\\maketitle')+1:buf.index('\\end{document}')]
    return buf

    

def protect_tex(line):
    # Protect characters so that they are not treated as special
    # commands for TeX
    
    line=line.replace('[','{[}')
    line=line.replace(']','{]}')
    line=line.replace('_','\_')
    line=line.replace('%','\%')
    line=line.replace('*','{*}')
    line=line.replace('^','\textasciicircum{}')
    
    return line


def protect_html(line):
    # Protect characters so that they are not treated as special
    # commands for HTML
    
    line=line.replace('<','&lt;')
    line=line.replace('>','&gt;')
    
    return line

def do_rebuild_file(source,dest,mode):
    if mode=='rebuild':
        return True

    if not os.path.exists(dest):
        if mode=='cached':
            print 'Error: Cached version of '+dest+ ' does not exist'
            sys.exit()
        
        print dest +' missing'

        return True
            
    is_newer = os.path.getmtime(source)>os.path.getmtime(dest)

    if mode=='auto':
        return is_newer

    if mode=='cached':
        return False


# This is the base class for deriving all configuration objects.
class ConfType:
    bibstyle='abbrv'
    urlext='php'
    otherrefs=[]


 # This is the class from which TeX configuration should be derived.
class TexConf(ConfType):
    basetype='tex'
    fext='.tex'
    widthstr='70ex'
    imagetype='eps'

    # Protect characters so that they are not treated as special
    # commands for TeX
    def protect(self,line):
        line=protect_tex(line)
        
        return line
    
    # Just append the latex-code.
    def displayformula_old(self,buf,obuf,fignum,caller):
        obuf.extend(buf)
        
    # Append a line of references
    def references(self,refbuf,obuf,caller):
        s=self.referenceheader+' '
        for item in refbuf:
            s=s+'\\cite{'+item+'}, '

        # append, and kill the last komma and space
        obuf.append(s[:-2])

    beginurl='\\href{'
    endurl='}'
    urlseparator='}{'

    referenceheader='\n\\textbf{References:}'

# This is the class from which PHP configurations should be
# derived.
class PhpConf(ConfType):
    basetype='php'
    fext='.php'
    widthstr=''
    imagetype='png'

    # Use bibtex2html to generate html references
    def references(self,reflist,obuf,caller):
        buf=call_bibtex2html(reflist,caller.c)

        obuf.append(self.referenceheader)
        obuf.extend(buf)
        

    beginurl='<a href="'
    endurl='</a>'
    urlseparator='">'

    beginboxheader='<b>'
    endboxheader='</b><br>'
 
    referenceheader='<br><br><H2>References:</H2>'

# This is the class from which Html configurations should be
# derived.
class HtmlConf(ConfType):
    basetype='html'
    fext='.html'
    widthstr=''
    imagetype='png'

    # Use bibtex2html to generate html references
    def references(self,reflist,obuf,caller):
        buf=call_bibtex2html(reflist,caller.c)

        obuf.append(self.referenceheader)
        obuf.extend(buf)
        

    beginurl='<a href="'
    endurl='</a>'
    urlseparator='">'

    beginboxheader='<b>'
    endboxheader='</b><br>'
 
    referenceheader='<br><br><H2>References:</H2>'

# This is the class from which Mat configurations should be
# derived.
class MatConf(ConfType):
    basetype='mat'

class BasePrinter(object):
    def __init__(self,conf,fname):
        self.c=conf

        # self.fname contains the name of the file
        # self.subdir contains the relative subdir in which the file is placed
        # self.fullname contains both
        self.fullname=fname
        self.subdir,self.fname=os.path.split(fname)

        # backdir contains a link to the root relative to the path the
        # the file is living in
        backdir=''
        if len(self.subdir)>0:
            backdir='../'


        #f=codecs.open(self.c.g.root+fname+'.m',encoding="utf-8")
        buf=safereadlines(self.c.g.root+fname+'.m')
        #f=file(self.c.g.root+fname+'.m')
        #buf=f.readlines()
        #f.close()

        self.is_oldformat = "%OLDFORMAT\n" in buf

        if self.is_oldformat:
            print 'Error: OLDFORMAT No longer supported.'
            sys.exit()

        self.buf_help=[]

        buf.reverse()

        while len(buf)>0:
            line=buf.pop()
            if line[0:8]=="function":
                continue
            if len(line)>0 and line[0]=="%":
                self.buf_help.append(line[1:])
            else:
                break

        self.parse()

        
    def writelines(self,fname,buf):
	# Create directory to hold the file if it does not already
	# exist.
	fullname=self.c.t.dir+fname
	base,name=os.path.split(fullname)
	if not os.path.exists(base):
	   os.mkdir(base)

        safewritelines(fullname,buf)



    def structure_as_webpage(self,maincontents,doctype):

        backdir=''
        if len(self.subdir)>0:
            backdir='../'

        includedir=backdir+self.c.t.includedir

        phpvars = self.print_variables()

        maincontents=map(lambda x:x.replace("'","\\'"),maincontents)

        # Opening of the php-file
        obuf=['<?php']
        obuf.append('$path_include="'+includedir+'";')
        obuf.append('include($path_include."main.php");')
        obuf.append('$doctype='+`doctype`+';')

        obuf.extend(phpvars)
        
        obuf.append("$content = '")
        obuf.extend(maincontents)
        obuf.append("';")

        obuf.append('printpage($title,$keywords,$seealso,$demos,$content,$doctype);')

        # Close PHP
        obuf.append('?>')

        return obuf

    def structure_as_webpage_html(self,maincontents,doctype):

      

        phpvars = self.print_variables()

        maincontents=map(lambda x:x.replace("'","\\'"),maincontents)

        # Opening of the php-file
        obuf=[' ']

        # header
        obuf.append("""<!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 4.0//EN"><html>
        <head>
        <meta http-equiv="Content-Type" content="text/html; charset=utf-8" />
        <META NAME="keywords" CONTENT="UNLocBoX, Matlab, optmization, convex, toolbox, reproducible research"/>
        <title>'+self.title+'</title>
        <link rel="stylesheet" href="include/html4css1.css" type="text/css">
        <link rel="stylesheet" href="include/rr.css" type="text/css">
        <link rel="stylesheet" href="include/color_text.css" type="text/css">
        <script type="text/javascript"
        src="http://cdn.mathjax.org/mathjax/latest/MathJax.js?config=TeX-AMS-MML_HTMLorMML">
        </script>
        </head>
        <body>
        <div id="container">
        <div id="header">""")

        # top of page
        obuf.append('<table style="height:100%; width:100%"> \n \
        <tr> \n \
        <td valign="top" width="65%"> \n \
        <h1>UNLocBoX-RR</h1> \n \
        <h2>- Reproducible research addendum-</h2> \n \
        </td> \n \
        <td valign="middle"> \n \
        <a href="/index.html"><img src="include/unlocbox.png" alt="UnLocX Logo" height="70"></a> \n \
        </td> \n \
        </tr> \n \
        </table> ')
        # menu

        menufile = open(self.c.t.dir+self.subdir+'/include/contentsmenu'+self.c.t.fext)
        obuf.extend(menufile.readlines())

        #content
        obuf.append('<div id="content">' )
        obuf.extend(maincontents)
        obuf.append('</div>\n')
        obuf.append('</div> \n \
        </div> \n \
        </body>\n \
        </html>')
        


        return obuf


class ExecPrinter(BasePrinter):


    def parse(self):

        space=' '
        out={}

        buf=self.buf_help

        buf.reverse()

        line=buf.pop().split()

        out['name']=line[0]

        if out['name'].lower()<>self.fname:
            print '  ERROR: Mis-match between function name and help text name.'
            print '  <'+out['name'].lower()+'> <'+self.fname+'>'
            sys.exit()

        out['description']=space.join(line[1:]).strip()
        
        self.title=out['name']+' - '+out['description']

        if len(out['description'])==0:
            print '  ERROR: Discription on first line is empty.'
            sys.exit()

        if out['description'][-1]=='.':
            print '  ERROR: Description line ends in a full stop.'
            sys.exit()

        out['body']=[]

        header_added=0

        # Counter to keep track of the number of executable blocks in
        # this file, used for numbering the figures correctly
        exec_n=0

        # Add setup code
        out['body'].append('.. default-role:: literal')
        out['body'].append('')

        # Append the internal reference lookup for this project
        out['body'].append('.. include:: '+self.c.g.root+'mat2doc/ref-internal.txt')

        # Append the lookups for other projects        
        for filename in self.c.g.otherrefs:
            out['body'].append('.. include:: '+self.c.g.root+'mat2doc/'+filename)

        out['body'].append('')

        # Add the title
        s=out['name']+' - '+out['description']
        out['body'].append(s)
        out['body'].append('='*len(s))
        
        for ii in range(len(buf)):
            
            if len(buf[ii].strip())>1:
                if not (buf[ii][0:3]=='   '):
                    print 'In function %s: Line does not start with three empty spaces.' % out['name']
                    sys.exit()
                else:
                    buf[ii]=buf[ii][3:]
            

        while len(buf)>0:

            line=buf.pop()

            # This check skips blank lines.
            if 'Usage' in line:
                out['body'].append('Usage')
                out['body'].append('-----')
                out['body'].append('')
                out['body'].append('::')
                out['body'].append('')
                out['body'].append('  '+line[6:].strip())
                line=buf.pop()
                # While the line does not start at zero.
                while not (len(line.strip())>0 and find_indent(line)==0):
                    s=line.strip()
                    if len(s)>0:
                        # When splitting the line, the function name
                        # always appears last, even if there is no "=" on
                        # the line.
                        #
                        # Similarly, then function name is always before "(" or ";"
                        usage_name=s.split('=')[-1].split('(')[0].split(';')[0].strip()
                        if usage_name<>self.fname:
                            print '  ERROR: Mis-match between function name and usage name.'
                            print '  <'+usage_name+'> <'+self.fname+'>'
                            print s
                            sys.exit()

                    
                    out['body'].append('  '+s)
                    line=buf.pop()

            if 'Input parameters' in line:
                out['body'].append('Input parameters')
                out['body'].append('----------------')
                out['body'].append('')
                line=buf.pop().rstrip()
                while len(line.strip())==0:
                    line=buf.pop().rstrip()
                idl=find_indent(line)
                # While the line does not start at zero.
                while not (len(line.strip())>0 and find_indent(line)==0):       
                    s=find_indent(line)
                    if s>0:
                        line=line[idl:]
                    if s==idl:
                        line=re.sub(':',' ',line,1)
                        line='--Q='+line
                    else:
                        line='    '+line

                    out['body'].append(line)
                    line=buf.pop().rstrip()
                # make sure the environment is closed
                out['body'].append('')

            if 'Output parameters' in line:
                out['body'].append('Output parameters')
                out['body'].append('-----------------')
                out['body'].append('')
                line=buf.pop().rstrip()
                while len(line.strip())==0:
                    line=buf.pop().rstrip()
                idl=find_indent(line)
                # While the line does not start at zero.
                while not (len(line.strip())>0 and find_indent(line)==0):       
                    s=find_indent(line)
                    if s>0:
                        line=line[idl:]
                    if s==idl:
                        line=re.sub(':',' ',line,1)
                        line='--Q='+line
                    else:
                        line='    '+line

                    out['body'].append(line)
                    line=buf.pop().rstrip()
                # make sure the environment is closed
                out['body'].append('')
            
            if ':::' in line:
                exec_n +=1

                out['body'].append(line.replace(':::','::'))

                # kill the following empty lines, until we find the next indented one
                line=buf.pop().rstrip()
                while len(line.strip())==0:
                    line=buf.pop().rstrip()
                idl=find_indent(line)

                codebuf=[]
                # add an empty line after the ::, because it was killed
                out['body'].append('')
                # While the line does not start at zero.
                while not ((len(buf)==0) or (len(line.strip())>0 and find_indent(line)==0)):       
                    codebuf.append(line)

                    out['body'].append(line)
                    line=buf.pop().rstrip()
                    
                # push back the last line, it was one too many.
                if find_indent(line)==0:
                    buf.append(line)

                # make sure the environment is closed
                out['body'].append('')

                outputprefix=self.c.t.dir+self.fullname+'_'+`exec_n`

                # Execute the code
                (outbuf,nfigs)=execplot(self.c.g.plotengine,codebuf,outputprefix,self.c.t.imagetype)

                # Append the result, if there is any
                if len(outbuf)>0:
                    out['body'].append('*This code produces the following output*::')
                    out['body'].append('')
                    for outline in outbuf:
                        out['body'].append('  '+outline)
                    out['body'].append('')                

                # Append the plots
                for i in range(nfigs):
                    out['body'].append('.. image:: '+self.fname+'_'+`exec_n`+'_'+`i+1`+'.'+self.c.t.imagetype)
                    if len(self.c.t.widthstr)>0:
                        out['body'].append('   :width: '+self.c.t.widthstr)
                    out['body'].append('')

                continue
      
            if 'See also' in line:
                (dummy,sep,s) = line.partition(':')
                if not(sep==':'):
                    raise Mat2docError('In function %s: See also line must contain a :' % out['name'])
                out['seealso']=map(lambda x:x.strip(',').lower(),s.split())
                continue

            if 'Demos' in line:
                (dummy,sep,s) = line.partition(':')
                if not(sep==':'):
                    raise Mat2docError('In function %s: Demos line must contain a :' % out['name'])
                out['demos']=map(lambda x:x.strip(',').lower(),s.split())
                continue

            if 'References:' in line:
                (dummy,sep,s) = line.partition(':')
                out['references']=s.strip().split()
                continue

            if not header_added:
                if line.strip()=='':
                    # Skip any initial blank lines
                    continue

                if not line[0]==' ':
                    # First real line encountered
                    out['body'].append('XXXDescription')
                    out['body'].append('--------------')
                    header_added=1

            out['body'].append(line.rstrip())


        self.parsed=out

        # Find the variables from parameter and usage lists.
        # self.find_pars()

        # Set the name
        self.name=self.parsed['name'].lower()
        
        # Add a final empty line, to make sure all environments are properly closed.
        out['body'].append('')

        # Read the code from a generated file into a buffer
        self.codebuf=saferead(self.c.t.codedir+self.fullname+'.m')
        #f=codecs.open(self.c.t.codedir+self.fullname+'.m',encoding="utf-8")
        #f=file(self.c.t.codedir+self.fullname+'.m')
        #self.codebuf=f.read()
        #f.close


    def print_code_html(self):
        
        highlightbuf=highlight(self.codebuf, MatlabLexer(), HtmlFormatter())
 
        maincontents=[]
    
        maincontents.append(self.c.t.hb+self.parsed['name']+' - '+self.parsed['description']+self.c.t.he)

        maincontents.append(self.c.t.hb+'Program code:'+self.c.t.he)

        maincontents.extend(highlightbuf.split('\n'))
	if self.c.t.basetype=='html':
            return self.structure_as_webpage_html(maincontents,2)
        else: 
            return self.structure_as_webpage(maincontents,2)


    def print_body(self,obuf):

        buf=self.parsed['body']

        # Initialize buffer
        buf_to_rst=''

        for line in buf:
            s=line.strip()
            if s=='':
                buf_to_rst+='\n'
                continue

            # Transform list definitions and formulae
            if len(line)>2 and line[2]=="'":
                line=re.sub("  '","--Q",line)
                line=re.sub("',","Q ",line)
                line=re.sub("' ","Q ",line)

            # Substite the correct formula code
            if '$' in line:
                words=line.split('$')
                line=words[0]
                for ii in range((len(words)-1)/2):
                    line+=':math:`'+words[2*ii+1]+'`'+words[2*ii+2]                

            buf_to_rst+=line+'\n'

        if 0: #self.c.t.basetype=='tex': make some debug here to be deleted
            if self.fname=='admm':
                print buf_to_rst
                sys.exit()


        buf=call_rst(buf_to_rst,self.c.t.basetype)

        # Clean up from table transformation

        splitidx=buf.find('XXXDescription')
        firstpart =buf[0:splitidx]
        secondpart=buf[splitidx:]

        if self.c.t.basetype=='php':
            firstpart =re.sub("--Q=","",firstpart)
            secondpart=re.sub("--Q","'",secondpart)
            secondpart=re.sub("Q ","',",secondpart)
            secondpart=re.sub("Q<","'<",secondpart)
        if self.c.t.basetype=='html':
            firstpart =re.sub("--Q=","",firstpart)
            secondpart=re.sub("--Q","'",secondpart)
            secondpart=re.sub("Q ","',",secondpart)
            secondpart=re.sub("Q<","'<",secondpart)

        if self.c.t.basetype=='tex':
            firstpart =re.sub("-{}-Q=","",firstpart)
            secondpart=re.sub("-{}-Q","'",secondpart)
            secondpart=re.sub("Q ","',",secondpart)
            secondpart=re.sub("Q]","']",secondpart)


        buf = firstpart+secondpart
        buf=  re.sub('XXXDescription','Description',buf)

        if 0: #self.c.t.basetype=='tex':
            if self.fname=='dwilt':
                print buf


        buf = rst_postprocess(buf,self.c.t.basetype)

        if 0: #self.c.t.basetype=='tex':
            if self.fname=='dwilt':
                print buf
                sys.exit()

            
        obuf.extend(buf)        

        # Do references
        if  self.parsed.has_key('references'):
            refbuf=self.parsed['references']
            self.c.t.references(refbuf,obuf,self)

        return

        

    def print_html(self):

        maincontents=[]

        self.print_body(maincontents)
        if self.c.t.basetype=='html':
            return self.structure_as_webpage_html(maincontents,1)
        else:
            return self.structure_as_webpage(maincontents,1)


    def print_tex(self,obuf):

        obuf.append('\subsection{'+self.c.t.protect(self.parsed['name'])+'}')

        obuf.append(self.c.t.protect(self.parsed['description']))
        obuf.append('')

        self.print_body(obuf)

        return obuf

    def write_the_file(self):
        if self.c.t.basetype=='php':
            self.write_html()  
        if self.c.t.basetype=='html':
            self.write_html()            

        if self.c.t.basetype=='tex':
            buf=self.print_tex([])
            self.writelines(self.fullname+self.c.t.fext,buf)
        

    def print_variables(self):
        # Convention used in this routine
        #   '  is the string delimiter in Python
        #   "  is the string delimiter in php

        obuf=[]

        # --- Title
        obuf.append('$title = "'+self.title+'";')

        # --- See also
        obuf.append('$seealso = array(')
        for see in self.parsed.get('seealso',[]):
            obuf.append('   "'+see+'" => "'+self.c.t.urlbase+
                        self.c.lookupsubdir[see]+'/'+see+self.c.t.fext+'",')
            
        obuf.append(');')

        
        obuf.append('$demos = array(')
        for see in self.parsed.get('demos',[]):
            obuf.append('   "'+see+'" => "'+self.c.t.urlbase+
                        self.c.lookupsubdir[see]+'/'+see+self.c.t.fext+'",')
            
        obuf.append(');')

        # --- Keywords
        obuf.append('$keywords = "'+self.title+'";')

        
        return obuf


        

class FunPrinter(ExecPrinter):

    def write_html(self):

        html_help_buf=self.print_html()
        self.writelines(self.fullname+self.c.t.fext,html_help_buf)

        html_code_buf=self.print_code_html()
        self.writelines(self.fullname+'_code'+self.c.t.fext,html_code_buf)


class ExamplePrinter(ExecPrinter):

    # Specialized version to fill in figures.    
    def write_html(self):

        # This functions does the following things different than the funnav
        #
        # - Executes the script and saves the images
        #
        # - Appends the output to the end.
        #
        # - does a search and replace to put in the correct filenames
        #   for the .. figure:: tags

        outputprefix=self.c.t.dir+self.fullname

        # Execute the code in the script
        
        (outbuf,nfigs)=execplot(self.c.g.plotengine,self.codebuf.split('\n'),
                                outputprefix,self.c.t.imagetype)

        
        # Go through the code and fill in the correct filenames
        counter = 1
        for idx in range(len(self.parsed['body'])):
            line = self.parsed['body'][idx]
            if line.find('figure::')>0:
                self.parsed['body'][idx] = line+' '+self.name+'_'+`counter`+'.'+self.c.t.imagetype
                if len(self.c.t.widthstr)>0:
                    out['body'].append('   :width: '+self.c.t.widthstr)

                counter += 1
        

        # Append the result, if there is any
        if len(outbuf)>0:
            self.parsed['body'].append('*This code produces the following output*::')
            self.parsed['body'].append('')
            for outline in outbuf:
                self.parsed['body'].append('  '+outline)
            self.parsed['body'].append('')                

        #self.write_output_html(outbuf)

        # Do the main plotting.
        html_help_buf=self.print_html()

        self.writelines(self.fullname+self.c.t.fext,html_help_buf)

        html_code_buf=self.print_code_html()
        self.writelines(self.fullname+'_code'+self.c.t.fext,html_code_buf)            
        

    def print_tex(self,obuf):

        # Go through the code and fill in the correct filenames in the figure directives
        counter = 1
        rstbuf=[]
        for line in self.parsed['body']:
            if line.find('figure::')>0:
                rstbuf.append(line+' '+self.name+'_'+`counter`+'.'+self.c.t.imagetype)
                if len(self.c.t.widthstr)>0:
                    rstbuf.append('   :width: '+self.c.t.widthstr)

                counter += 1
            else:
                rstbuf.append(line)

        self.parsed['body']=rstbuf

        # Execute the inherited print_tex, to do the main work
        ExecPrinter.print_tex(self,obuf)

        outputprefix=self.c.t.dir+self.fullname

        # Execute the code in the script
        (outbuf,nfigs)=execplot(self.c.g.plotengine,self.codebuf.split('\n'),
                                outputprefix,self.c.t.imagetype)

        if 0:
            obuf.append('\\subsubsection*{Output}')
            
            obuf.append('\\begin{verbatim}')

            for line in outbuf:
                obuf.append(line)

            obuf.append('\\end{verbatim}')
        obuf.append('\\clearpage')
        return obuf

class ContentsPrinter(BasePrinter):

    def parse(self):

        html=[]
        files=[]
        sep='-'

        buf=self.buf_help

        buf.reverse()

        line=buf.pop()

        # First line defines the title.
        self.title=line.strip()

        obuf=[]

        while len(buf)>0:

            line=buf.pop()
                        
            if (sep in line) and not (isnewblock(line)):
                # Fix the preceeding line, if it is a text line
                if obuf[-1][0]=='text':
                    obuf[-1][0]='caption'
                
                # Put the line back in buf for parsing.
                buf.append(line)
                pairs=parse_pairs(sep,buf,find_indent(line))
                for (key,sep,val) in pairs:
                    obuf.append(['li',key.lower(),val])
                    files.append(key.lower())

                # Append an empty line, it is eaten by parse_pairs
                obuf.append(['text',''])
            else:
                obuf.append(['text',line.strip()])

        self.files=files

        self.parsed=obuf


    def print_html(self):

        maincontents=[]

        maincontents.append(self.c.t.hb+self.title+self.c.t.he)

        ul_on=0
        for line in self.parsed:

            if line[0]=='li':
                if ul_on==0:
                    maincontents.append('<ul>')
                    ul_on=1

                maincontents.append('<li><a href="'+line[1]+self.c.t.fext+'">'+line[1]+'</a> - '+line[2]+'</li>')
                continue

            # Turn of list mode, we have encountered a non-list line
            if ul_on==1:
                maincontents.append('</ul>')
                ul_on=0

            if line[0]=='text':
                maincontents.append(line[1])
                continue

            if line[0]=='caption':
                maincontents.append(self.c.t.hb+line[1]+self.c.t.he)
                continue

        self.html = self.structure_as_webpage(maincontents,0)


    def print_rst(self):

        maincontents=[]

        # Append the internal reference lookup for this project
        maincontents.append('.. include:: '+self.c.g.root+'mat2doc/ref-internal.txt')

        maincontents.append(self.title)
        maincontents.append('='*len(self.title))


        ul_on=0
        for line in self.parsed:

            if line[0]=='li':
                if ul_on==0:
                    maincontents.append('')
                    ul_on=1

                maincontents.append('  * |'+line[1]+'|_ - '+line[2])
                continue

            # Turn of list mode, we have encountered a non-list line
            if ul_on==1:
                maincontents.append('')
                ul_on=0

            if line[0]=='text':
                # Substite the correct formula code
                if '$' in line[1]:
                    words=line[1].split('$')
                    line[1]=words[0]
                    for ii in range((len(words)-1)/2):
                        line[1]+=':math:`'+words[2*ii+1]+'`'+words[2*ii+2]

                maincontents.append(line[1])
                continue

            if line[0]=='caption':
                maincontents.append(line[1])
                maincontents.append('-'*len(line[1]))
                continue

        if 0:
            for line in maincontents:
                print line

            sys.exit()

        
        outstr=''
        for line in maincontents:
            outstr+=line+'\n'

        return outstr


    def print_menu(self):

        obuf=[]
        obuf.append('<?php')
        obuf.append('$menu = array(')

        # Add a unique number to each line to make them different
        # In the code below " is used to delimit python strings
        # and ' is used for the php strings, because we need to include a " into the innermost
        # string
        uniq_no=0
        for line in self.parsed:
            uniq_no+=1
            if line[0]=="li":
                obuf.append("   'li"+`uniq_no`+"' => '"+"<a href=\""+line[1]+self.c.t.fext+"\">"+line[1]+"</a>',")

            if line[0]=="caption":
                obuf.append("   'caption"+`uniq_no`+"' => '"+line[1]+"',")

        obuf.append(");")
        obuf.append("?>")
                    
        return obuf
    def print_menu_html(self):

        obuf=[]
        obuf.append(' <div id="navigation"> \n \
        <ul>')
	obuf.append('<li><a href="index.html">Home </a> </li>')
        for line in self.parsed:
            if line[0]=="li":
                obuf.append('<li>'+'<a href="'+line[1]+self.c.t.fext+'">'+line[1]+'</a></li>')
                obuf.append('<li><ul><li>'+'<a href="'+line[1]+'_code.html">'+line[1]+' code</a></li></ul></li>')
        obuf.append('</ul>')
        obuf.append('</div>')
                    
        return obuf

    def print_tex(self):

        obuf=[]

        obuf.append('\graphicspath{{'+self.subdir+'/}}') 

        obuf.append('\\chapter{'+self.title+'}')

        for line in self.parsed:

            # Skip text lines
            if line[0]=='text':
                continue

            # Turn captions into sections
            if line[0]=='caption':
                obuf.append('\section{'+self.c.t.protect(line[1])+'}')
                continue

            if line[0]=='li':
                # Parse the file.
                fname=os.path.join(self.subdir,line[1])
                obuf.append('\input{'+fname+'}')
                continue
            
        return obuf



    def write_the_file(self):

        if self.c.t.basetype=='php':
            rststr=self.print_rst()
            phpstr=call_rst(rststr,'php')
            buf = rst_postprocess(phpstr,'php')
            buf = self.structure_as_webpage(buf,0)


            #self.print_html()
            
            self.writelines(os.path.join(self.subdir,'index.php'),buf)
            
            menu=self.print_menu()
            self.writelines(self.subdir+'/contentsmenu'+self.c.t.fext,menu)
            
        if self.c.t.basetype=='html':
            rststr=self.print_rst()
            phpstr=call_rst(rststr,'html')

            menu=self.print_menu_html()
            self.writelines(self.subdir+'/include/contentsmenu'+self.c.t.fext,menu)


            buf = rst_postprocess(phpstr,'html')
            buf = self.structure_as_webpage_html(buf,0)


            #self.print_html()
            
            self.writelines(os.path.join(self.subdir,'index.html'),buf)
            


        if self.c.t.basetype=='tex':
            obuf=self.print_tex()
            self.writelines(self.fullname+'.tex',obuf)
    

    def print_variables(self):
        # Convention used in this routine
        #   '  is the string delimiter in Python
        #   "  is the string delimiter in php

        obuf=[]

        # --- Title
        obuf.append('$title = "'+self.title+'";')

        obuf.append('$seealso = array();')
        obuf.append('$demos = array();')
        
        # --- Keywords
        obuf.append('$keywords = "'+self.title+'";')

        return obuf


def isblank(line):
    if len(line.split())==0:
        return 1
    return 0
    
def isnewblock(line):
    if line[3]!=' ':
        return 1
    return 0

def parse_pairs(sep,buf,parent_indent):
    out=[]
    while len(buf)>0:
        line=buf.pop()
        ind=line.find(sep)

        if ind==-1:
            # No separator found.
            
            if find_indent(line)>parent_indent:
                # If this line is more indented than its parent,
                # add it to the list but with no separator
                out.append(('','',line[ind+1:].strip()))
            else:
                # End of block reached.
                # Put the line back into the buffer and stop
                buf.append(line)
                break
        else:            
            if ind+1==len(line.rstrip()):
                # The separator appears at the very end, this is a
                # new block.
                # Put the line back into the buffer and stop
                buf.append(line)
                break
            else:
                # Append the line, with separator
                out.append((line[0:ind].strip(),sep,line[ind+1:].strip()))
    return out


# Remove TeX-only charachters
def clean_tex(line):
    
    line=line.replace('$','')
    
    return line


def execplot(plotengine,buf,outprefix,ptype):
    tmpdir='/tmp/'
    tmpfile='plotexec'
    tmpname=tmpdir+tmpfile+'.m'
    fullpath=os.path.dirname(outprefix)
    funname =os.path.basename(outprefix).split('.')[0]

    # printtype determines the correct printing flag in Matlab / Octave
    printtype={'png':'-dpng',
               'eps':'-depsc'}[ptype]

    # Clear old figures
    p=os.listdir(fullpath)
    # Match only the beginning of the name, to avoid sgram maching resgram etc.
    oldfiles=filter(lambda x: x[0:len(funname)]==funname,p)
    for fname in oldfiles:
        os.remove(os.path.join(fullpath, fname))

    f=codecs.open(tmpname,'w',encoding="utf-8")
           
    f.write("disp('MARKER');\n");

    f.write("""
set(0, 'DefaultFigureVisible', 'off');
%set(0, 'DefaultAxesVisible', 'off');
""")
    
    # Matlab does not terminate if there is an error in the code, so
    # we use a try-catch statment to capture the error an exit cleanly.
    f.write("try\n");

    for line in buf:
        f.write(line+'\n')        

    f.write("""
for ii=1:numel(findall(0,'type','figure'))
  figure(ii);
  %X=get(gcf,'PaperPosition');
  %set(gcf,'PaperPosition',[X(1) X(2) .7*X(3) .7*X(4)]);
""")
    # Matlab does not support changing the resolution (-r300) when
    # printing to png in nodisplay mode.
    f.write("print(['"+outprefix+"_',num2str(ii),'."+ptype+
            "'],'"+printtype+"')\n")
    
    f.write("end;\n")

    f.write("catch err\ndbstack\nerr.message\ndisp('ERROR IN THE CODE');end;");

    # Matlab needs an explicit 'exit' statement, otherwise the interpreter
    # hangs around.
    if plotengine=='matlab':
	f.write('pause(1);\n');
	f.write('exit\n');

    f.close()

    if plotengine=='octave':
       # -q suppresses the Octave startup message.
       s='octave -q '+tmpname
    else:
       s='matlab -nodesktop -nodisplay -r "addpath \''+tmpdir+'\'; '+tmpfile+';"'    

    print '  Producing '+outprefix+' using '+plotengine

    try:
        output=check_output(s,shell=True,stderr=PIPE)
    except CalledProcessError as s: 
        print '  WARNING: Exit code from Matlab',s.returncode
        output=s.output

    pos=output.find('MARKER')
    if pos<0:
        raise Mat2docError('For the output %s: The plot engine did not print the MARKER output.' % outprefix)

    # Remove everything until and including the marker
    output=output[pos+7:].strip()

    if 'ERROR IN THE CODE' in output:
        print '--------- Matlab code error ----------------'
        print output        
        raise Mat2docError('For the output %s: There was an error in the Matlab code.' % outprefix)

    # If string was empty, return empty list, otherwise split into lines.
    if len(output)==0:
        outbuf=[]
    else:
        outbuf=output.split('\n')

    # Find the number of figures
    p=os.listdir(fullpath)
    # Match only the beginning of the name, to avoid sgram maching resgram etc.
    nfigs=len(filter(lambda x: x[0:len(funname)]==funname,p))

    print '  Created %i plot(s)' % nfigs

    # Sometimes Matlab prints the prompt on the last line, it ends
    # with a ">" sign, which should otherwise never terminate the output.
    if (len(outbuf)>0) and (outbuf[-1][-1]=='>'):
        outbuf.pop()

    return (outbuf,nfigs)


def print_matlab(conf,ifilename,ofilename):
    inputf=file(ifilename,'r')

    ibuf=inputf.readlines()
    inputf.close()

    outputf=file(ofilename,'w')

    # Determine the name of the function
    name = os.path.basename(ifilename).split('.')[0]

    ibuf.reverse()

    line=ibuf.pop()
    
    if line[0:8]=="function":
        # Write the function line
        outputf.write(line)
        line=ibuf.pop()

    # figure counter for the demos
    nfig=1

    # Do the help section
    while line[0]=='%' and len(ibuf)>0:

        if  'References:' in line:
            (dummy,sep,s) = line.partition(':')
            reflist = s.strip().split()

            buf=call_bibtex2html(reflist,conf)

            obuf=[]

            # Skip lines containing hyperlinks
            for rline in buf:
                if rline[:1]=='[':
                    continue

                if rline[:6]=='</tr>':
                    obuf.append(rline+'\n')
                    obuf.append('</table><br><table><tr>\n')
                    continue

                obuf.append(rline+'\n')

            # Write the clean HTML to a temporary file and process it using
            # lynx.
            outname=conf.g.tmpdir+'reflist'
            f=file(outname+'.html','w')
            f.writelines(obuf)
            f.close()

            s='lynx -dump '+outname+'.html > '+outname+'.txt'
            os.system(s)

            ftxt=file(outname+'.txt')
            buf=ftxt.readlines()
            ftxt.close()

            buf=map(lambda x:x.strip(),buf)

            outputf.write('%   References:\n')
            for rline in buf[0:]:
                outputf.write('%     '+rline+'\n')

            line=ibuf.pop()
            continue

        # Figures in demos
        if '.. figure::' in line:
            # Pop the empty line
            line_empty=ibuf.pop()
            if len(line_empty[1:].strip())>0:
                print 'Error: Figure definition must be followed by a single empty line.'
                sys.exit()
                
            heading=ibuf.pop()

            if len(heading[1:].strip())==0:
                print 'Error: Figure definition must be followed by a single empty line.'
                sys.exit()

            outputf.write('%   Figure '+`nfig`+': '+heading[1:].strip()+'\n')
            line=ibuf.pop()

            if len(line[1:].strip())>0:
                print 'Error: Figure definition must be followed by a single line header and an empty line.'
                sys.exit()

            nfig+=1

            continue

        # Keep all other lines.
        if len(line)>2:

            # remove the display math sections. FIXME: This will not
            # correctly handle display math in nested environments.
            if '.. math::' in line:
                line=ibuf.pop()

                # Keep removing lines until we hit an empty line.
                while len(line[1:].strip())>0:
                    line=ibuf.pop()

            # Remove inline formula markup
            line=line.replace('$','')

            # Math substitutions
            line=line.replace('\ldots','...')
            line=line.replace('\\times ','x')
            line=line.replace('\leq','<=')
            line=line.replace('\geq','>=')
            line=line.replace('\cdot ','*')
            line=line.replace('\pm ','+-')
            line=line.replace('\mathbb','')
            # Kill all remaining backslashes
            line=line.replace('\\','')

            # Remove hyperlink markup
            line=line.replace('`<','')
            line=line.replace('>`_','')

            # Convert internal links to uppercase
            p=re.search(' \|.*?\|_',line)
            if p:
                line=line[0:p.start(0)+1]+line[p.start(0)+2:p.end(0)-2].upper()+line[p.end(0):]

            # Uppercase the function name appearing inside backticks, and remove them
            p=re.search('`.*?`',line)
            if p:
                line=line[0:p.start(0)]+line[p.start(0)+1:p.end(0)-1].replace(name,name.upper())+line[p.end(0):]

            #line=line.replace('`','')

            # Remove stars
            line=line.replace(' *',' ')
            line=line.replace('* ',' ')
            line=line.replace('*,',',')
            line=line.replace('*.','.')
            line=line.replace('*\n','\n')

            # Remove start of comments
            line=line.replace(' .. ','    ')

            if line.find(':::')>0:
                line=line.replace(':::',':')
                

            # Convert remaining :: into :
            line=line.replace('::',':')

            outputf.write(line)
        else:        
            outputf.write(line)

        line=ibuf.pop()

    # Append url for quick online help
    # Find the name of the file + the subdir in the package 
    shortpath=ifilename[len(conf.t.dir):-2]
    outputf.write('%\n')
    outputf.write('%   Url: '+conf.t.urlbase+shortpath+'.'+conf.t.urlext+'\n')
    
    # --- Append Copyright if defined. --
    # Append empty line to seperate copyright from help section
    outputf.write('\n')
    buf=conf.g.copyright(conf.g)

    for cline in buf:
        outputf.write('% '+cline)        

    # Append the rest (non-help section)
    while len(ibuf)>0:
        outputf.write(line)
        line=ibuf.pop()

    # Write the last line, and close
    outputf.write(line)
    outputf.close()


# This factory function creates function or script file objects
# depending on whether the first word of the first line is 'function'
def matfile_factory(conf,fname):
    
    buf=safereadlines(conf.g.root+fname+'.m')
    #f=file(conf.g.root+fname+'.m')
    #buf=f.readlines()
    #f.close()

    if buf[0].split()[0]=='function':
        return FunPrinter(conf,fname)
    else:
        return ExamplePrinter(conf,fname)

def find_indent(line):
    ii=0
    while (ii<len(line)) and (line[ii]==' '):
        ii=ii+1
    return ii
