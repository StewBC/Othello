ASCII/Curses Othello in Python for Windows, Mac and Linux

I decided to learn Python.  I wanted a project to use as a base, so I chose
Othello.

The AI in this game is very simple.  It looks at some number of moves, up to
every possible move, for the most tiles it can take this turn.  It uses a
structure that "backs" the board to make playing certain tiles have an
advantage.  An "advantage" just means the "number of pieces captured" by
playing on that square is boosted by some amount.  

This process can be repeated up to some number of "levels".  The levels are
the look-ahead mechanism.  Level 0 is the current color, level 1 would be
the counter moves for the opponent, level 2 would be the current colors'
counter to the opponents' counter move, etc.  The scores are summed, adding
tiles taken by the current color and subtracting tiles taken by the
opponent.  The idea is that in the long term, better decisions are made.

I am not clear that it really makes the game play much better.  I did have
fun with Breadth set to 5 and Depth set to 3.  Not too slow and at least
a little bit challanging.  With both set to 0 (the default), the game is
still quite fun, I think.

    V1.0 - 11 Jan 2017 - Initial Release - Windows only.
    V1.1 - 12 Jan 2017 - Mac and Linux support.
    V1.2 - 12 Jan 2017 - ESC brings up in-game menu.
    V1.3 - 13 Jan 2017 - Added help and Undo/Redo. Made board look nicer.
    V1.4 - 14 Jan 2017 - Added recursive AI and settings for this AI.

If anyone reads the code and has comments, please let me know!  As I did
this to learn, I would love any feedback that helps me improve.
swessels@email.com
