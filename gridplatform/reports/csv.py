# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import unicode_literals

import cStringIO
from contextlib import closing

import unicodecsv
from django.http import HttpResponse

__all__ = ['generate_csv', 'serve_csv']


class _excel_semicolon(unicodecsv.excel):
    delimiter = b';'


def generate_csv(data, header=None):
    """
    Format provided data as CSV and return it as a byte string.

    :param data: Iterable yielding data for each CSV row.

    :param header: Optional header row data.

    :return: Bytestring with Excel-compatible CSV-formatted data.
    """
    with closing(cStringIO.StringIO()) as outfile:
        # BOM included for Excel-compatibility --- assuming that this is the
        # "start of the file"
        bom = b'\xef\xbb\xbf'
        outfile.write(bom)
        writer = unicodecsv.writer(outfile, dialect=_excel_semicolon)
        if header is not None:
            writer.writerow(header)
        if isinstance(data, list):
            for line in data:
                writer.writerow(line)
        else:
            for utility_type, values in data.iteritems():
                for line in values['data']:
                    writer.writerow(line)

        return outfile.getvalue()


def serve_csv(data, header=None):
    """
    Format provided data as CSV and return it as a text/csv HttpResponse.

    :see: :func:`.generate_csv`.
    """
    csv = generate_csv(data, header)
    return HttpResponse(csv, content_type='text/csv')
