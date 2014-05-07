import re
import codecs
import contextlib
import chardet
import os

VALIDATION_BIN = 'node ' + os.path.dirname(os.path.realpath(__file__)) +\
                 os.sep + 'validate-vtt.js'

class SubtitleException(Exception):
  """ Raised when there are errors with subtitles """
  pass

@contextlib.contextmanager
def vtt_open(path_or_file, mode):
  """
  Taken from Ned Batchelder: http://stackoverflow.com/a/6783680/390977

  Allows a string to be passed or a file object
  """
  if isinstance(path_or_file, basestring):
    f = file_to_close = open(path_or_file, mode)
  else:
    f = path_or_file
    file_to_close = None

  yield f

  if file_to_close:
    file_to_close.close()

def is_valid(f):
  """ Returns a boolean representing whether or not the given file is valid
  File can either be a string representing the path, or a FileStorage object
  """
  import tempfile
  
  if hasattr(f, 'save'): # for werkzeug.datastructures.FileStorage objects
    with tempfile.NamedTemporaryFile() as t: # TODO: pipe contents directly to cmd
      contents = f.read()
      t.write(contents)
      t.flush()
      f.seek(0)
      return os.system(VALIDATION_BIN + ' ' + t.name) == 0
  else:
    return os.system(VALIDATION_BIN + ' ' + f) == 0

def from_srt(input_f, output_f):
  """
    Takes an input SRT file or filename and writes out VTT contents to the given 
    output file or filename
  """
  import tempfile

  timestamp = "\n(\d{2}:\d{2}:\d{2}),(\d{3}\s*-->\s*\d{2}:\d{2}:\d{2}),(\d{3})\s*\n"

  with vtt_open(input_f, 'r') as f:
    orig = f.read()
    detect = chardet.detect(orig)
    encoding = detect['encoding']
    confidence = detect['confidence']

    if confidence < 0.9:
      encoding = 'cp1252' # standard for SubRip files

    contents = orig.decode(encoding)
  
  # strip carriage returns for consistency's sake
  contents = re.sub("\r\n","\n",contents)

  # remove cue numbering
  regex = re.compile('\d+(?=' + timestamp + ')', re.MULTILINE)
  contents = re.sub(regex, "", contents)

  # change timing 
  contents = re.sub(timestamp, "\\1.\\2.\\3\n", contents)

  # append correct header
  contents = 'WEBVTT\n\n' + contents

  # validate first
  f = tempfile.NamedTemporaryFile()
  f.write(contents.encode('utf-8'))
  f.flush()
  if not is_valid(f.name):
    raise SubtitleException("SRT could not be converted to a valid subtitle file.")

  with vtt_open(output_f, 'w') as o:
    o.write(contents.encode('utf-8'))

def shift_time(input_f, output_f, offset_secs):
  """
    Takes the time codes in the input file and adds (or removes) the offset in
    seconds from each cue, writing to the output file.

    Example:
      # add ten seconds to each cue of a Mr. Rogers subtitle file
      shift_time("Mr. Rogers S3E5.vtt", "Mr. Rogers S3E5.fixed.vtt", 10)

      # subtract 1 hour from each cue of a subtitle file
      shift_time("QVC_greatest_hits.vtt", "qvc_fixed.vtt", -3600)
      
      # using file objects
      shift_time(open('bad.vtt','r'), open('good.vtt','w'), 42)
  """
  import re
  from datetime import datetime, timedelta
    
  # arbitrary dates to extract the timestamp
  YEAR = 1989
  MONTH = 9
  DAY = 6
  
  FORMAT          = '%H:%M:%S.%f'
  DELTA           = timedelta(seconds = offset_secs)
  EXTRA_PAD_STRIP = -3

  def datetime_from_string(val):

    # expects format \d{2}:\d{2}:\d{2}\.\d{3}
    times                = val.split(':')
    hour                 = int(times[0])
    minute               = int(times[1])
    second, deciseconds  = [int(x) for x in times[2].split('.')]
    micro                = deciseconds*1000

    return datetime(YEAR, MONTH, DAY, hour, minute, second, micro)

  def string_from_datetime(time):
    return (time + DELTA).strftime('%H:%M:%S.%f')[:EXTRA_PAD_STRIP]

  def do_sub(matches):
    if matches is None:
      return

    first = matches.group(1)
    second = matches.group(2)

    return string_from_datetime( datetime_from_string(first) ) +\
           " --> " +\
           string_from_datetime( datetime_from_string(second) ) +\
           "\n"

  rx = re.compile("^(\d{2}:\d{2}:\d{2}\.\d{3}) --> (\d{2}:\d{2}:\d{2}\.\d{3})\s*$")
  
  with vtt_open(input_f, 'r') as read_me:
    with vtt_open(output_f, 'w') as write_me:
      for line in read_me:
        line = line.decode('utf-8')
        fixed = rx.sub(do_sub, line)
        write_me.write( fixed.encode('utf-8') )
