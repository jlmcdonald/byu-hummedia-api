import pytest, io
from .. import vtt

def test_from_srt(ASSETS):
  f = io.BytesIO()
  vtt.from_srt(ASSETS + 'subs.srt', f)
  compare = open(ASSETS + 'subs.vtt', 'r')
  assert f.getvalue() == compare.read()

def test_from_srt_file(ASSETS):
  i = open(ASSETS + 'subs.srt')
  o = io.BytesIO()
  vtt.from_srt(i, o)
  compare = open(ASSETS + 'subs.vtt', 'r')
  assert o.getvalue() == compare.read()

def test_shift_time(ASSETS):
  f = io.BytesIO()
  vtt.shift_time(ASSETS + 'subs.vtt', f, 10)
  compare = open(ASSETS + 'subs+10.vtt', 'r')
  assert f.getvalue() == compare.read()

def test_shift_time_file(ASSETS):
  i = open(ASSETS + 'subs.vtt', 'r')
  o = io.BytesIO()
  vtt.shift_time(i, o, 10)
  i.close()
  compare = open(ASSETS + 'subs+10.vtt', 'r')
  assert o.getvalue() == compare.read()
