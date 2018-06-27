
import textwrap

from .utils import Record, assert_type
from .multiline import Multiline, get_multilines
from .color import (
    LINE,
    BACKGROUND,
    DARKER,
    EVEN_DARKER,
    Soft,
    Shade
)


__all__ = [
    'Span',
    'BoxMarkup',
    'BoxLabelMarkup',
    'LineMarkup',
    'LineLabelMarkup',
    'AsciiMarkup',
]


class Span(Record):
    __attributes__ = ['start', 'stop', 'type']

    def __init__(self, start, stop, type=None):
        assert_type(start, int)
        assert_type(stop, int)
        if start >= stop:
            raise ValueError('expected start < stop')
        self.start = start
        self.stop = stop
        self.type = type

    def __lt__(self, other):
        if self.start != other.start:
            return self.start < other.start
        else:
            if self.stop != other.stop:
                return self.stop < other.stop
            else:
                if self.type != other.type:
                    if self.type is None:
                        return True
                    if other.type is None:
                        return False
                    return self.type < other.type
                else:
                    return False  # eq


class Html(object):
    def _repr_html_(self):
        return ''.join(self.as_html)


class Ascii(object):
    def _repr_pretty_(self, printer, cycle):
        for line in self.as_ascii:
            printer.text(line)
            printer.break_()


class Markup(Record):
    __attributes__ = ['text', 'spans']

    def __init__(self, text, spans):
        self.text = str(text)
        self.spans = sorted(spans)
        for span in self.spans:
            assert_type(span, Span)
        self.multilines = list(get_multilines(self.spans))


class BoxMarkup(Html, Markup):
    label = False
    color = True

    @property
    def as_html(self):
        yield '<div style="white-space: pre-wrap">'
        previous = 0
        for span in self.spans:
            start, stop, type = span
            yield self.text[previous:start]

            if self.color:
                background = BACKGROUND[type]
                border = DARKER[background]
                label = EVEN_DARKER[background]
            else:
                background = Shade.YELLOW
                border = Shade.DARK_YELLOW
                label = Shade.DARKER_YELLOW
            yield (
                '<span style="'
                'padding: 0.15em; '
                'border-radius: 0.25em; '
                'border: 1px solid {border}; '
                'background: {background}'
                '">'.format(
                    background=background,
                    border=border
                )
            )
            yield self.text[start:stop]
            if self.label and span.type:
                yield (
                    '<sup style="'
                    'font-size: 0.7em; '
                    'color: {color};'
                    '">'.format(
                        color=label
                    )
                )
                yield span.type
                yield '</sup>'
            yield '</span>'
            
            previous = stop
        yield self.text[previous:]
        yield '<div>'


class BoxLabelMarkup(BoxMarkup):
    label = True
    color = False


class LineMarkup(Html, Markup):
    @property
    def as_html(self):
        yield (
            '<div style="'
            'line-height: 1.6em; '
            'white-space: pre-wrap'
            '">'
        )
        previous = 0
        for multi in self.multilines:
            start, stop, _ = multi
            yield self.text[previous:start]

            for line in multi.lines:
                padding = 1 + line.level * 3
                color = LINE[line.type]
                yield (
                    '<span style="'
	            'border-bottom: 2px solid {color}; '
	            'padding-bottom: {padding}px'
                    '">'.format(
                        padding=padding,
                        color=color
                    )
                )
            yield self.text[start:stop]            
            for _ in multi.lines:
                yield '</span>'

            previous = stop
        yield self.text[previous:]
        yield '<div>'


class LineLabelMarkup(Html, Markup):
    @property
    def as_html(self):
        yield (
            '<div style="'
            'line-height: 1.6em; '  # 1.5 is default
            'white-space: pre-wrap'
            '">'
        )
        previous = 0
        for multi in self.multilines:
            start, stop, _ = multi
            yield self.text[previous:start]

            text = self.text[start:stop]
            if not text.strip():
                yield text
            else:
                yield (
                    '<span style="'
	            'border-bottom: 2px solid {color}; '
	            'padding-bottom: 1px'
                    '">'.format(
                        color=Soft.BLUE
                    )
                )
                yield text
                yield '</span>'
            
                yield (
                    '<span style="'
                    'display: inline-block; '
                    'margin-left: 1px; '
                    'font-size: 7px;'
                    '">'
                )
                types = [
                    _.type
                    for _ in multi.lines
                    if _.type is not None
                ]
                if len(types) == 1:
                    yield types[0]
                elif len(types) > 1:
                    for line in multi.lines:
                        yield '<span style="display: block; height: 7px;">'
                        yield line.type
                        yield '</span>'
                yield '</span>'

            previous = stop
        yield self.text[previous:]
        yield '<div>'


class Wrapper(textwrap.TextWrapper):
    def __init__(self, width):
        super(Wrapper, self).__init__(
            width,
            expand_tabs=False,
            replace_whitespace=False,
            drop_whitespace=False
        )

    def __call__(self, text):
        start = 0
        lines = text.splitlines()
        for index, line in enumerate(lines):
            if index < len(lines) - 1:
                line = line + ' '  # replace \n with ' '
            for fold in self.wrap(line):
                stop = start + len(fold)
                yield start, stop, fold
                start = stop


class AsciiMarkup(Ascii, Markup):
    def __init__(self, text, spans, width=70):
        Markup.__init__(self, text, spans)
        self.wrapper = Wrapper(width)

    @property
    def as_ascii(self):
        index = 0
        for start, stop, line in self.wrapper(self.text):
            slices = []
            while index < len(self.multilines):
                multi = self.multilines[index]
                if multi.start >= stop:
                    break
                slice = Multiline(
                    max(multi.start, start),
                    min(multi.stop, stop),
                    multi.lines
                )
                slices.append(slice)
                if multi.stop <= stop:
                    index += 1
                else:
                    break
            
            yield line.replace('\t', ' ')

            if slices:
                height = max(
                    line.level
                    for slice in slices
                    for line in slice.lines
                ) + 1
                width = len(line)
                matrix = [
                    [' ' for _ in range(width)]
                    for row in range(height)
                ]
                for slice in slices:
                    for line in slice.lines:
                        for x in range(slice.start, slice.stop):
                            matrix[line.level][x - start] = '-'
                for slice in slices:
                    for line in slice.lines:
                        if line.type and line.start == slice.start:
                            size = line.stop - line.start
                            space = width - (slice.start - start)
                            type = line.type[:min(size, space)]
                                
                            for x, char in enumerate(type):
                                matrix[line.level][slice.start - start + x] = char
                for row in matrix:
                    yield ''.join(row)