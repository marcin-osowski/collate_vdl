#!/usr/bin/env python3
"""A simple utility to collate dumpvdl2 messages

"""

import collections
import dateutil.parser
import time
import re

LOG_FILE="vdl2.log"

class Message:
  def __init__(self, raw):
    self.raw = raw
    self._parse_acquisition()
    self._parse_endpoints()

  def __repr__(self):
    return "%s (%s) -> %s (%s)" % (self.from_hex, self.from_type, self.to_hex, self.to_type)

  def __str__(self):
    return "\n".join(raw)

  def _parse_acquisition(self):
    self.timestamp = None
    for line in self.raw:
      matched = re.fullmatch(r"\[([0-9 :A-Z-]*)\] \[([0-9.]*)\] \[.*\] \[([0-9.]*) dB\].*", line)
      if matched:
        self.timestamp = dateutil.parser.parse(matched.group(1))
        self.freq = float(matched.group(2))
        self.dB = float(matched.group(3))

  def _parse_endpoints(self):
    self.from_hex = None
    self.from_type = None
    self.to_hex = None
    self.to_type = None
    for line in self.raw:
      matched = re.fullmatch(r"([A-F0-9]+) \(([^,]*).*\) -> ([A-F0-9]+) \(([^,]*).*\): (.*)", line)
      if matched:
        self.from_hex = matched.group(1)
        self.from_type = matched.group(2)
        self.to_hex = matched.group(3)
        self.to_type = matched.group(4)


class HexToMessages:
  def __init__(self):
    self.map = collections.defaultdict(lambda: [])

  def add_message(self, message):
    if message.from_hex:
      self.map[message.from_hex].append(message)
    if message.to_hex:
      self.map[message.to_hex].append(message)


def tail_lines(f):
  lastpos = 0
  while True:
    line = f.readline()
    newpos = f.tell()
    if lastpos != newpos:
      yield line
    else:
      time.sleep(0.1)
    lastpos = newpos


def tail_messages(f):
  message_buffer = []
  for line in tail_lines(f):
    if line == "\n":
      if message_buffer:
        yield Message(message_buffer)
        message_buffer = []
    else:
      message_buffer.append(line.rstrip("\n"))


def data_reader(log_filename, hex_to_messages):
  with open(log_filename, "r") as f:
    for message in tail_messages(f):
      hex_to_messages.add_message(message)


if __name__ == "__main__":
  hex_to_messages = HexToMessages()
  data_reader(LOG_FILE, hex_to_messages)
