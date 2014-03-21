'''
  Takes an input SRT file or filename and writes out VTT contents to the given 
  output file or filename
'''
def from_srt(input, output):
  import re

  timestamp = "(\d{2}:\d{2}:\d{2}),(\d{3}\s*-->\s*\d{2}:\d{2}:\d{2}),(\d{3})\s*"

  try:
    contents = input.read()
  except (IOError, AttributeError):
    with open(input, 'r') as f:
      contents = f.read()
  
  # strip carriage returns for consistency's sake
  contents = re.sub("\r\n","\n",contents)

  # remove cue numbering
  regex = re.compile('\d+\n(?=' + timestamp + ')', re.MULTILINE)
  contents = re.sub(regex, "", contents)

  # change timing 
  contents = re.sub(timestamp, "\\1.\\2.\\3\n", contents)

  # append correct header
  contents = "WEBVTT\n\n" + contents
  
  try:
    output.write(contents)
  except (IOError, AttributeError):
    with open(output, 'w') as o:
      o.write(contents)

'''
  Takes the time codes in the input file and adds (or removes) the offset in
  seconds from each cue, writing to the output file.

  Example:
    # add ten seconds to each cue of a Mr. Rogers subtitle file
    shift_time("Mr. Rogers S3E5.vtt", "Mr. Rogers S3E5.fixed.vtt", 10)

    # subtract 1 hour from each cue of a subtitle file
    shift_time("QVC_greatest_hits.vtt", "qvc_fixed.vtt", -3600)
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
  
  close_out = False #whether or not we should close our input and output files
  close_in = False
  read_me = input_f
  write_me = output_f

  if not hasattr(input_f, 'read'):
    read_me = open(input_f, 'r')
  
  if not hasattr(output_f, 'write'):
    write_me = open(output_f, 'w')

  for line in read_me:
    write_me.write( rx.sub(do_sub, line) )

  if close_in:  read_me.close()
  if close_out: write_me.close()