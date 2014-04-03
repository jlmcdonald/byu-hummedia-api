import re
import codecs
import contextlib

'''
Taken from Ned Batchelder: http://stackoverflow.com/a/6783680/390977

Allows a string to be passed or a file object
'''
@contextlib.contextmanager
def vtt_open(path_or_file, mode):
  if isinstance(path_or_file, basestring):
    f = file_to_close = open(path_or_file, mode)
  else:
    f = path_or_file
    file_to_close = None

  yield f

  if file_to_close:
    file_to_close.close()

'''
  Takes an input SRT file or filename and writes out VTT contents to the given 
  output file or filename
'''
def from_srt(input_f, output_f):
  timestamp = "\n(\d{2}:\d{2}:\d{2}),(\d{3}\s*-->\s*\d{2}:\d{2}:\d{2}),(\d{3})\s*\n"

  with vtt_open(input_f, 'r') as f:
    contents = f.read().decode('utf-8')
  
  # strip carriage returns for consistency's sake
  contents = re.sub("\r\n","\n",contents)

  # remove cue numbering
  regex = re.compile('\d+(?=' + timestamp + ')', re.MULTILINE)
  contents = re.sub(regex, "", contents)

  # change timing 
  contents = re.sub(timestamp, "\\1.\\2.\\3\n", contents)

  # append correct header
  contents = 'WEBVTT\n\n' + contents
 
  with vtt_open(output_f, 'w') as o:
    o.write(contents.encode('utf-8'))

'''
  Takes the time codes in the input file and adds (or removes) the offset in
  seconds from each cue, writing to the output file.

  Example:
    # add ten seconds to each cue of a Mr. Rogers subtitle file
    shift_time("Mr. Rogers S3E5.vtt", "Mr. Rogers S3E5.fixed.vtt", 10)

    # subtract 1 hour from each cue of a subtitle file
    shift_time("QVC_greatest_hits.vtt", "qvc_fixed.vtt", -3600)
    
    # using file objects
    shift_time(open('bad.vtt','r'), open('good.vtt','w'), 42)
'''
def shift_time(input_f, output_f, offset_secs):
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
