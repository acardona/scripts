import sys, os


def shortenAuthors(authors, printAuthors=True):
  """
  Example:
  authors = "Schlegel, Philipp and Yin, Yijie and Bates, Alexander S and Dorkenwald, Sven and Eichler, Katharina and Brooks, Paul and Han, Daniel S and Gkantia, Marina and Dos Santos, Marcia and Munnelly, Eva J and Badalamente, Griffin and Serratosa Capdevila, Laia and Sane, Varun A. and Fragniere, Alexandra M. C. and Kiassat, Ladann and Pleijzier, Markus W. and Stürner, Tomke and Tamimi, Imaan F. M. and Dunne, Christopher R. and Salgarella, Irene and Javier, Alexandre and Fang, Siqi and Perlman, Eric and Kazimiers, Tom and Jagannathan, Sridhar R. and Matsliah, Arie and Sterling, Amy R. and Yu, Szi-chieh and McKellar, Claire E. and FlyWire Consortium and Costa, Marta and Seung, H. Sebastian and Murthy, Mala and Hartenstein, Volker and Bock, Davi D. and Jefferis, Gregory S X E"
  
  The output is like:
  "P. Schlegel and Y. Yin and ..."
  """

  s = authors.split(" and ")

  a = []
  for e in s:
    es = e.split(", ")
    if len(es) > 1:
      names = es[1].split(" ")
      a.append("".join(["%s." % name[0] for name in names]) + " " + es[0])
    else:
      a.append(es[0]) # e.g. "FlyWire Consortium"

  o = " and ".join(a)
  if printAuthors:
    print(o)
  return o
  
  
if len(sys.argv) < 2:
  print('Usage: python shorten-bibtex-authors.py "Schlegel, Philip and <...>"')
  sys.exit(0)

shortenAuthors(sys.argv[1])

