#!/usr/bin/env python

from string import Template

from pandocfilters import toJSONFilter, RawBlock, RawInline


def unpack_code(value, language):
    ''' Unpack the body and language of a pandoc code element.

    Args:
        value       contents of pandoc object
        language    default language
    '''
    [[label, classes, attributes], contents] = value

    if len(classes) > 0:
        language = classes[0]

    caption = None
    captionA = [a[1] for a in attributes if a[0] == 'caption']
    if len(captionA) > 0:
        caption = captionA[0]

    attributes = [a for a in attributes if a[0] != 'caption']
    attributes = ', '.join('='.join(x) for x in attributes)

    return {'label': label, 'contents': contents, 'language': language,
            'attributes': attributes, 'caption': caption}


def minted(key, value, format, meta):
    ''' Use minted for code in LaTeX.

    Args:
        key     type of pandoc object
        value   contents of pandoc object
        format  target output format
        meta    document metadata
    '''
    if format != 'latex':
        return

    # Determine what kind of code object this is.
    if key == 'CodeBlock':
        template = Template('''
\\begin{listing}
\\begin{minted}[$attributes]{$language}
$contents
\\end{minted}
\\caption{$caption}
\\label{$label}
\\end{listing}
''')
        Element = RawBlock
    elif key == 'Code':
        template = Template('\\mintinline[$attributes]{$language}{$contents}')
        Element = RawInline
    else:
        return

    # print(value, file=sys.stderr)
    code = unpack_code(value, 'text')
    # print(code, file=sys.stderr)

    return [Element(format, template.substitute(code))]


if __name__ == '__main__':
    toJSONFilter(minted)
