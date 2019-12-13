# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import unicode_literals

import codecs
import datetime
import logging
import os
import os.path
import re
import shutil
import subprocess
import tempfile
import time

from django.core.exceptions import ImproperlyConfigured
from django.http import HttpResponse
from django.template.loader import render_to_string
from django.template.response import TemplateResponse
from django.utils.formats import get_format
from django.views.generic.base import TemplateResponseMixin
from django.views.generic.detail import BaseDetailView

import braces.views
import pytz


logger = logging.getLogger(__name__)


class LatexError(Exception):
    """
    Exception representing errors during LaTeX run.
    """
    def __init__(self, log_file_name):
        """
        Construct :class:`.LatexError` containing errors from a LaTeX
        log-file.

        :param log_file_name: Name of log file to read actual
            LaTeX-error from.
        """
        with codecs.open(log_file_name, 'r', 'iso8859-1') as log_file:
            log = log_file.read()
        short = None
        start = re.search('^! [^\n]* Error:', log, re.MULTILINE)
        if start:
            short = log[start.start():]
            end = re.search(
                "^Here is how much of TeX's memory you used:$",
                short, re.MULTILINE)
            if end:
                short = short[:end.start()]
            self.value = log_file_name + '\n\n\n' + short + '\n\n\n' + log
        else:
            self.value = log_file_name + '\n\n\n' + log

    def __str__(self):
        return self.value


def compile_pdf(file_basename, content):
    """
    Compiles the given LaTeX ``content``.

    Wraps :func:`_compile_pdf` so that it uses a temponary output
    directory, that is deleted again after a successful compile, and
    left for debug inspection upon failure.

    :param file_basename:  The base name of the generated PDF.
    :param content: The LaTeX to be compiled.

    :return: the contents of the resulting PDF.
    """
    tmp_dir = tempfile.mkdtemp(prefix='latex')
    pdf_file_name = _compile_pdf(file_basename, content, tmp_dir)
    with open(pdf_file_name, 'rb') as pdf_file:
        data = pdf_file.read()
    shutil.rmtree(tmp_dir)
    return data


def _compile_pdf(file_basename, content, out_dir):
    """
    Compiles the given LaTeX ``content``

    :param file_basename:  The base name of the generated PDF.
    :param content: The LaTeX to be compiled.
    :param out_dir: The directory in which to perform the compilation.

    :return: The full path of the compiled PDF document.
    """
    start_time = time.time()
    tex_file_name = os.path.join(out_dir, file_basename + '.tex')
    pdf_file_name = os.path.join(out_dir, file_basename + '.pdf')
    log_file_name = os.path.join(out_dir, file_basename + '.log')
    with codecs.open(tex_file_name, mode='wb', encoding='utf-8') as f:
        f.write(content)
    with codecs.open(tex_file_name, mode='wb', encoding='utf-8') as f:
        f.write(content)
    # -halt-on-error and -interaction=nonstopmode to have the process terminate
    # rather than wait for interactive commands...
    command = [
        'xelatex',
        '-halt-on-error', '-interaction=nonstopmode',
        tex_file_name,
    ]
    with open('/dev/null', 'w') as FNULL:
        for n in range(4):
            # we run LaTeX up to 4 times...
            if subprocess.call(
                    command, cwd=out_dir,
                    stdin=FNULL, stdout=FNULL, stderr=FNULL) != 0:
                raise LatexError(log_file_name)
            with codecs.open(log_file_name, 'r', 'iso8859-1') as log:
                # stop sooner if LaTeX does not tell us to rerun
                if all(['Rerun to get' not in line and
                        'Rerun LaTeX' not in line
                        for line in log]):
                    break
    if not os.path.exists(pdf_file_name):
        raise LatexError(log_file_name)
    end_time = time.time()
    logger.debug('PDF generated in %f seconds', end_time - start_time)
    return pdf_file_name


def _generate_pdf(template, data, tmp_dir):
    """
    Generates a PDF from the LaTeX that result from rendering a
    template in a given context in a given directory.

    :param template: The Django template that renders a LaTeX
        document.
    :param data: The template context in which to render the template.
    :param tmp_dir: The directory in which to compile the LaTeX
        document.

    :return: The full path to the generated PDF.
    """
    file_root, ext = os.path.splitext(os.path.basename(template))
    return _compile_pdf(file_root, render_to_string(template, data), tmp_dir)


def _generate_gnuplot(plot, out_dir):
    """
    Generate a gnuplot plot.

    :param plot: The string of commands to run in GNU plot.

    :param outdir: This is the directory in which gnuplot will be run (and thus
        generate it's output).

    :see: :class:`gridplatform.reports.tests.GnuPlotTest` for an
        example.
    """
    with open('/dev/null', 'w') as FNULL:
        p = subprocess.Popen(
            ['gnuplot'], cwd=out_dir,
            stdin=subprocess.PIPE, stdout=FNULL, stderr=FNULL)
        p.communicate(plot.encode('utf-8'))
        p.wait()
        if p.returncode != 0:
            raise subprocess.CalledProcessError(
                returncode=p.returncode,
                cmd='gnuplot - \n%s' % plot)


def generate_pdf(template, data, title, report_type, customer, gnuplots=[]):
    """
    Generate a PDF from the named template instantiated with the
    provided data using LaTeX.

    :param template: Template for tex file.

    :param data: Data for template instantiation.

    :param title: Title for PDF file.

    :param report_type: "Report type" for document footer.

    :param gnuplots: List of gnuplot scripts to be run before
        generating the PDF.

    :return: Byte string with contents of generated PDF file.
    """

    data['meta'] = {
        'title': title,
        'type': report_type,
        'generation_time': datetime.datetime.now(pytz.utc),
        'customer': customer,
    }
    tmp_dir = tempfile.mkdtemp(prefix='latex')
    for gnuplot in gnuplots:
        _generate_gnuplot(gnuplot, tmp_dir)
    pdf_file_name = _generate_pdf(template, data, tmp_dir)
    with open(pdf_file_name, 'rb') as pdf_file:
        data = pdf_file.read()
    shutil.rmtree(tmp_dir)
    return data


def serve_pdf(template, data, title, report_type, customer):
    """
    Generate a PDF from the named template instantiated with the
    provided data using LaTeX and return it as a application/pdf
    HttpResponse.

    :see: :func:`.generate_pdf`
    """
    pdf = generate_pdf(template, data, title, report_type, customer)
    return HttpResponse(pdf, content_type='application/pdf')


class PDFTemplateResponse(TemplateResponse):
    """
    TemplateResponse wrapper which compiles its rendered data string
    to PDF with LaTeX.
    """
    @property
    def rendered_content(self):
        template = self.resolve_template(self.template_name)
        context = self.resolve_context(self.context_data)
        content = template.render(context)
        template_path = template.name

        file_basename, ext = os.path.splitext(
            os.path.basename(template_path))
        if ext != '.tex':
            file_basename = 'report'
        return compile_pdf(file_basename, content)


class PDFDetailView(
        braces.views.LoginRequiredMixin,
        TemplateResponseMixin, BaseDetailView):
    """
    Generic PDF-generation view for use where the normal setup with background
    data collection and saving the resulting PDF to the database does not
    provide any clear benefits.

    Designed as a replacement for the :func:`.serve_pdf` function...
    """
    content_type = 'application/pdf'
    response_class = PDFTemplateResponse

    document_title = None
    document_customer = None
    document_type = None

    def get_document_title(self):
        """
        :return: The document title.
        """
        if self.document_title is not None:
            return self.document_title
        return unicode(self.object)

    def get_document_customer(self):
        """
        :return: The customer for whom the document is served.
        """
        if self.document_customer is not None:
            return self.document_customer
        elif hasattr(self.object, 'customer'):
            return self.object.customer
        else:
            raise ImproperlyConfigured(
                "PDFDetailView requires either 'document_customer', "
                "a 'customer' attribute on its model object or "
                "an implementation of 'get_document_customer()'.")

    def get_document_type(self):
        """
        :return: The document type.  If not set explicitly it is derived
            from the base name of a template.
        """
        if self.document_type is not None:
            return self.document_type
        template_path = self.get_template_names()[0]
        file_basename, ext = os.path.splitext(
            os.path.basename(template_path))
        return file_basename

    def get_context_meta(self):
        """
        :return: The meta dictionary available in the template context.
        """
        return {
            'title': self.get_document_title(),
            'type': self.get_document_type(),
            'generation_time': datetime.datetime.now(pytz.utc),
            'customer': self.get_document_customer(),
        }

    def get_context_data(self, **kwargs):
        """
        Specialization of
        :meth:`django.views.generic.TemplateView.get_context_data`.

        :return: The context data made available by the view during
            template rendering.
        """
        context = {
            'meta': self.get_context_meta(),
            'DECIMAL_SEPARATOR': get_format('DECIMAL_SEPARATOR'),
            'THOUSAND_SEPARATOR': get_format('THOUSAND_SEPARATOR'),
        }
        context.update(kwargs)
        return super(PDFDetailView, self).get_context_data(**context)
