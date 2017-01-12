Othello in Python for Windows

Yesterday (10 Jan 2017) I decided to learn Python.  I wanted a project to use
as a base, so I chose Othello.

The AI in this game is very simple, and thus not very good.  It looks for the
most tiles it can take this turn, and it uses a structure that "backs" the 
board to make playing certain tiles have an advantage.  An "advantage" just
means the "number of pieces captured" by playing on that square is boosted
by some amount.  Perhaps later I will make a better evaluator.

This version is Windows specific (uses msvcrt for kbhit in menu(), for
example)

What have I learnt?  I like Python!  I almost gave up after struggling with
tabs and spaces but after I set Sublime Text 3 up to treat tabs as 4 spaces
when writing python and making it so F7 runs the code in a cmd window, it 
went well.

What did I use to learn Python?  Google and mostly Stack Overflow but also 
docs.python.org.
