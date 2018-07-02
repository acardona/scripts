#!/usr/bin/env python
'''
Copyright 2018 Albert Cardona, sapristi@gmail.com

This work is in the public domain.

'''

# Only needed if the script is not directly in the installation directory
import sys
sys.path.append('/usr/share/inkscape/extensions')

import inkex
from copy import copy


class Word:
  def __init__(self, x, text): 
    self.x = x
    self.text = text

class SplitKernedText(inkex.Effect):
  def __init__(self):
    inkex.Effect.__init__(self)
    self.OptionParser.add_option("-s", "--separation", action="store", type="float", dest="separation", default="1.0", help="Maximum separation to split two characters")
    self.OptionParser.add_option("-p", "--preserve", action="store", type="inkbool", dest="preserve", default="True", help="Preserve original")

  def extract_text_nodes(self, parent, child):
    """ Return a text node with x,y attributes. """
    text = inkex.etree.Element(inkex.addNS("text", "svg"), parent.attrib)
    x = child.get("x") or parent.get("x")
    y = child.get("y") or parent.get("y")
    text.set("x", x)
    text.set("y", y)
    text.append(copy(child))
    return text

  def plain_string(self, elem):
    """ Recursively extract text.
        Returns a list of words. """
    words = []
    if elem.text:
      words.append(elem.text)
    for n in elem:
      words.extend(self.plain_string(n))
      if n.tail:
        words.append(n.tail)
    return words

  def split_kerned_text(self, node):
    """ Returns a list of new text nodes. """
    new_text_nodes = []

    separation = self.options.separation
    preserve = self.options.preserve

    # Find all the tspan entries, which are direct children of the node
    text_nodes = [self.extract_text_nodes(node, n) for n in node]

    for text_node in text_nodes:
      # Keep non-empty entries
      xs = map(float, filter(len, text_node.get("x").split(' ')))
      ys = map(float, filter(len, text_node.get("y").split(' ')))
      
      if len(xs) < 2:
        inkex.debug("This text element does not contain text kerned in the X axis.")
        continue

      if len(ys) > 1:
        inkex.debug("Can't yet handle kerning in the Y axis.")
        continue

      strings = filter(None, map(lambda a: a.strip(), self.plain_string(node))) # without empty strings
      if not strings or len(strings) > 1:
        inkex.debug("Can only handle text that appears as single strings. You chose: ##" + ",".join(strings) + "##")
        continue

      word = strings[0]

      if len(word) != len(xs):
        inkex.debug("Can only handle kerned text for which there is an x coordinate for every character.")
        continue

      # Split according to X-axis kerning and the specified maximum separation
      i = 0
      tokens = []
      token = Word(xs[0], word[0])
      for c2, x1, x2 in zip(word[1:], xs[:-1], xs[1:]):
        if abs(x2 - x1) > separation:
          # Start new token
          tokens.append(token)
          token = Word(x2, c2)
        else:
          # Append character to existing token
          token.text += c2
        i += 1
      tokens.append(token)

      try:
          from simplestyle import parseStyle
          fontsize = parseStyle(text.get("style"))["font-size"]
      except:
        fontsize = "12px"
      fs = self.unittouu(fontsize) # !?!?!

      # Create a new text node for each token
      for token in tokens:
        tspan = inkex.etree.Element(inkex.addNS("tspan", "svg"))
        tspan.text = token.text
        new_text_node = inkex.etree.Element(inkex.addNS("text", "svg"), text_node.attrib)
        tspan.set(inkex.addNS("role", "sodipodi"), "line")
        new_text_node.set("x", str(token.x))
        new_text_node.set("y", str(ys[0]))

        new_text_node.append(tspan)
        new_text_nodes.append(new_text_node)

    return new_text_nodes

    # Split if y is different than prior character,
    # or if distance in x is larger than the defined separation.

  def effect(self):
    """ Applies the effect. """
    preserve = self.options.preserve

    for id, node in self.selected.iteritems():
      if not (node.tag == inkex.addNS("text", "svg") or node.tag):
        inkex.debug("Please select only plain text elements.")
      else:
        new_text_nodes = self.split_kerned_text(node)
        # 
        for n in new_text_nodes:
          node.getparent().append(n)
        # Preserve original element if requested
        if not preserve and new_text_nodes:
          parent = node.getparent()
          parent.remove(node)


# Execute extension
SplitKernedText().affect()

