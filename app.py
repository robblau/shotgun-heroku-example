# Standard imports
import os
import cgi
import json
import shutil
import urllib
import zipfile
import tempfile

# Report Lab
import reportlab.lib.styles
from reportlab.lib.units import inch
from reportlab.lib import utils, colors
from reportlab.lib.pagesizes import letter
from reportlab.platypus import Table, Paragraph, Image, Frame
from reportlab.platypus import TableStyle, FrameBreak
from reportlab.platypus.doctemplate import PageTemplate, BaseDocTemplate

# Shotgun API
import shotgun_api3


def get_image(path, max_width, max_height):
    if (path is None):
        styles = reportlab.lib.styles.getSampleStyleSheet()
        return Paragraph('', styles['BodyText'])

    img = utils.ImageReader(path)
    img_width, img_height = img.getSize()
    if (img_width > max_width):
        ratio = float(max_width) / float(img_width)
        img_height = img_height * ratio
        img_width = max_width

    if (img_height > max_height):
        ratio = float(max_height) / float(img_height)
        img_width = img_width * ratio
        img_height = max_height
    return Image(path, width=img_width, height=img_height)


def report(fname, shot, versions):
    # pdf properties
    title = "Report"
    author = "Rob Blau"

    # define frames for page layout
    page = PageTemplate(frames=[
        Frame(x1=0.1*inch, y1=8.9*inch, width=3*inch, height=2*inch),  # shot thumbnail
        Frame(x1=0.1*inch, y1=0.1*inch, width=8.3*inch, height=4*inch),  # versions table
    ])

    # create the doc
    doc = BaseDocTemplate(
        fname,
        pagesize=letter,
        pageTemplates=page,
        title=title,
        author=author,
    )

    # styles
    styles = reportlab.lib.styles.getSampleStyleSheet()

    # content
    story = []

    # shot thumbnail
    data = [['Shot Thumbnail'], [get_image(shot['image'], 3*inch, 1.5*inch)]]
    shot_thumbnail = Table(data, colWidths=3*inch)
    shot_thumbnail.setStyle(TableStyle([
        ('BOX', (0,0), (-1,-1), 0.25, colors.black),
        ('INNERGRID', (0,0), (-1,-1), 0.25, colors.black),
        ('TEXTCOLOR', (0,0), (0,0), colors.white),
        ('BACKGROUND', (0,0), (0,0), colors.black),
        ('ALIGN', (0,1), (0,1), 'CENTER'),
    ]))
    story.append(shot_thumbnail)
    story.append(FrameBreak())

    # versions grid
    data = [
        ['Versions', '', '', ''],
        [Paragraph('<b>%s</b>' % t, styles['BodyText']) for t in ['Status', 'Name', 'Notes', 'Frame Range']],
    ]
    for v in versions:
        data.append([
            Paragraph(v['sg_status_list'] or '', styles['BodyText']),
            Paragraph(v['code'] or '', styles['BodyText']),
            Paragraph(v['description'] or '', styles['BodyText']),
            Paragraph(v['frame_range'] or '', styles['BodyText']),
        ])
    version_table = Table(data)
    version_table.setStyle(TableStyle([
        ('BOX', (0,0), (-1,-1), 0.25, colors.black),
        ('INNERGRID', (0,0), (-1,-1), 0.25, colors.black),
        ('TEXTCOLOR', (0,0), (0,0), colors.white),
        ('BACKGROUND', (0,0), (0,0), colors.black),
        ('SPAN', (0,0), (-1, 0)),
    ]))
    story.append(version_table)
    story.append(FrameBreak)

    # and save
    doc.build(story)


class App(object):
    def __call__(self, environ, start_response):
        # parse params
        params = cgi.FieldStorage(fp=environ['wsgi.input'], environ=environ)
        shot_ids = [int(i) for i in params.getvalue('selected_ids', []).split(',')]
        server_hostname = params.getvalue('server_hostname')
        # connect to Shotgun
        sg = shotgun_api3.shotgun.Shotgun(
            'https://%s' % server_hostname,
            os.environ['SHOTGUN_SCRIPT_NAME'],
            os.environ['SHOTGUN_SCRIPT_KEY'],
        )

        # grab shots
        filter = {
            'logical_operator': 'or',
            'conditions': [{'path': 'id', 'relation': 'is', 'values': [id]} for id in shot_ids],
        }
        fields = ['sequence.Sequence.code', 'image', 'code']
        shots = sg.find('Shot', filter, fields=fields)

        # grab versions
        filter = {
            'logical_operator': 'or',
            'conditions': [{'path': 'entity', 'relation': 'is', 'values': [shot]} for shot in shots],
        }
        fields = ['code', 'image', 'entity', 'description', 'frame_range', 'sg_status_list']
        versions = sg.find('Version', filter, fields=fields)
        versions_by_shot = dict()
        for version in versions:
            versions_by_shot.setdefault(version['entity']['id'], []).append(version)

        tmpdir = tempfile.mkdtemp(prefix='report')
        old_dir = os.getcwd()
        os.chdir(tmpdir)
        try:
            shot_pdfs = []
            for shot in shots:
                # grab thumbnails
                tmp_thumb = '%s.jpg' % shot['code']
                if shot['image'] is not None:
                    urllib.urlretrieve(shot['image'], tmp_thumb)
                    shot['image'] = tmp_thumb

                # create pdf frames
                tmpfile = '%s.pdf' % shot['code']
                report(tmpfile, shot, versions_by_shot[shot['id']])
                shot_pdfs.append(tmpfile)

            # zip them up
            tmpzip = 'reports.zip'
            archive = zipfile.ZipFile(tmpzip, mode='w')
            archive.comment = 'This is a report.'
            for shot_pdf in shot_pdfs:
                archive.write(shot_pdf, compress_type=zipfile.ZIP_DEFLATED)
            archive.close()

            # start response
            status = '200 OK'
            response_headers = [
                ('Content-Type', 'application/zip'),
                ('Content-Disposition', 'attachment; filename="reports.zip"'),
            ]
            start_response(status, response_headers)

            f_obj = open(tmpzip, "rb")
            if 'wsgi.file_wrapper' in environ:
                return environ['wsgi.file_wrapper'](f_obj, 1024)
            else:
                return iter(lambda: f_obj.read(1024), '')
        finally:
            os.chdir(old_dir)
            shutil.rmtree(tmpdir)

app = App()
