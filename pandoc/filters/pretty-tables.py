#!/usr/bin/env python

"""
Pandoc filter to render latex tables. The default pandoc tables don't use vertical lines
which looks weird, so generate the tables with this filter as desired.
"""

from pandocfilters import RawBlock, RawInline, Para, toJSONFilter


def latex(s):
    return RawBlock('latex', s)


def inlatex(s):
    return RawInline('latex', s)


def tbl_caption(s):
    return Para([inlatex(r'\caption{')] + s + [inlatex(r'}')])


def tbl_alignment(s):
    aligns = {
        'AlignDefault': r'\raggedright',
        'AlignLeft': r'\raggedright',
        'AlignCenter': r'\centering',
        'AlignRight': r'\raggedleft',
    }

    cols = len(s)
    result = []

    for col in s:
        align = aligns[col[0]['t']]
        width = col[1]['c']
        result.append(r'>{%s\arraybackslash}p{(\columnwidth - %d\tabcolsep) * \real{%.4f}}' % (align, cols*2, width))

    return result


def tbl_headers(s):
    result = [inlatex(r'\hline' '\n')]

    for header in s[1][0][1]:
        result.append(inlatex(r'\textbf{'))
        result.extend(header[4][0]['c'])
        result.append(inlatex(r'}'))
        result.append(inlatex(' & '))
    result.pop()
    result.append(inlatex(r' \\' '\n' r'\hline\hline'))

    return Para(result)


def tbl_contents(s):
    result = []

    for row in s[0][3]:
        for col in row[1]:
            result.extend(col[4][0]['c'])
            result.append(inlatex(' & '))
        result.pop()
        result.append(inlatex(r' \\' '\n'))
        result.append(inlatex(r'\hline' '\n'))

    return Para(result)


def process_table(key, value, format, meta):
    if format != 'latex':
        return

    if key == 'Table':
        caption = value[1]
        alignment = value[2]
        headers = value[3]
        contents = value[4]

        # there are `Table` elements in meta, skip them by looking at the caption value
        if len(caption[1]) == 0:
            return

        latex_alignment = '\n  |' + '\n  |'.join(tbl_alignment(alignment)) + '|'
        return [
            latex(r'\begin{table}[h]'),
            latex(r'\centering'),
            latex(r'\begin{tabular}{@{} %s @{}}' % latex_alignment),
            tbl_headers(headers),
            tbl_contents(contents),
            latex(r'\end{tabular}'),
            tbl_caption(caption[1][0]['c']),
            latex(r'\end{table}')
        ]


if __name__ == '__main__':
    toJSONFilter(process_table)
