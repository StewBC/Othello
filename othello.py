"""
Othello, using curses, by Stefan Wessels.
Versions:
    V1.0 - 11 Jan 2017 - Initial Release - Windows only.
    V1.1 - 12 Jan 2017 - Mac and Linux support.
    V1.2 - 12 Jan 2017 - ESC brings up in-game menu.
    V1.3 - 13 Jan 2017 - Added help and Undo/Redo. Made board look nicer.
    V1.4 - 14 Jan 2017 - Added recursive AI and settings for this AI.
"""

import curses
import time
import copy

windows = False
try:
    import msvcrt
    windows = True
except ImportError as e:
    import sys
    import select

INPUT_MOTION    = [curses.KEY_UP, curses.KEY_DOWN]
INPUT_SELECT    = [curses.KEY_ENTER, 10, 13]
INPUT_BACKUP    = 27 # ESC key
INPUT_UNDO      = 117
INPUT_REDO      = 114
INPUT_COMMAND   = [INPUT_BACKUP, INPUT_UNDO, INPUT_REDO]
SCROLL_SPEED    = 0.15
BLANK           = ' '
WHITE           = 'O'
BLACK           = 'X'
CELL_W          = 3
CELL_H          = 1

CR_BLUE_CYAN    = 1
CR_BLACK_CYAN   = 2
CR_WHITE_CYAN   = 3
CR_RED_CYAN     = 4
CR_YELLOW_BLUE  = 5
CR_GREEN_BLUE   = 6
CR_WHITE_BLUE   = 7
CR_WHITE_GREEN  = 8
CR_BLACK_WHITE  = 10

# menu system that draws a menu in the middle of the screen
def menu(title, menuItems, menuHeight, maxWidth, scroller):
    maxLen = len(title)
    numMenuItems = len(menuItems)
    for i in range(numMenuItems):
        length = len(menuItems[i])
        if length > maxLen:
            maxLen = length

    sy = int(max(0, screenY/2-(menuHeight/2)-1))
    sx = int(max(0, screenX/2-(maxLen/2)-1))
    maxLen = int(min(maxWidth-2, maxLen))

    scrollIndex = 0
    scrollLength = len(scroller)
    
    stdscr.addstr(sy, sx, ' {:^{width}} '.format(title[:maxLen], width=maxLen), curses.color_pair(CR_YELLOW_BLUE))
    sy += 1
    stdscr.addstr(sy, sx, " " * (maxLen+2), curses.color_pair(CR_YELLOW_BLUE))
    sy += 1
    
    for i in range(numMenuItems):
        stdscr.addstr(sy+i, sx, ' {:{width}} '.format(menuItems[i][:maxLen], width=maxLen), curses.color_pair(CR_WHITE_BLUE))
    
    for i in range(i+1, menuHeight):
        stdscr.addstr(sy+i, sx, " " * (maxLen+2), curses.color_pair(CR_WHITE_BLUE))
    
    i = 0
    key = 0
    start = time.time()
    while True:
        stdscr.addstr(sy+i, sx, '>{:{width}}<'.format(menuItems[i][:maxLen], width=maxLen), curses.color_pair(CR_WHITE_GREEN))
        keyPressed = 0
        if windows:
            keyPressed = msvcrt.kbhit()
        else:
            dr, dw, de = select.select([sys.stdin], [], [], 0)
            if not dr == []:
                keyPressed = 1
        if keyPressed:
            key = stdscr.getch()
            if key in INPUT_MOTION:
                stdscr.addstr(sy+i, sx, ' {:{width}} '.format(menuItems[i][:maxLen], width=maxLen), curses.color_pair(CR_WHITE_BLUE))
                if key == curses.KEY_UP:
                    i -= 1
                    if i < 0:
                        i = numMenuItems-1
                elif key == curses.KEY_DOWN:
                    i += 1
                    if numMenuItems == i:
                        i = 0
        
        stdscr.addstr(sy+menuHeight, sx, " " + scroller[scrollIndex:scrollIndex+maxLen], curses.color_pair(CR_GREEN_BLUE))
        remain = scrollLength-scrollIndex
        while remain < maxLen:
            string = scroller[:maxLen-remain]
            stdscr.addstr(sy+menuHeight, sx+1+remain, string, curses.color_pair(CR_GREEN_BLUE))
            remain += len(string)
        stdscr.addstr(" ", curses.color_pair(CR_GREEN_BLUE))
        stdscr.refresh()

        if time.time()-start > SCROLL_SPEED:
            scrollIndex += 1
            start = time.time()
            if scrollIndex == scrollLength:
                scrollIndex = 0

        if key in INPUT_SELECT or key == INPUT_BACKUP:
            break
    
    stdscr.clear()
    if key == INPUT_BACKUP:
        return -1
    
    return i

# backs up/restores the board, turn and score
class UndoRedo:
    def __init__(self):
        self.boardStack = []
        self.attribStack = []
        self.curr = -1
        self.top = -1

    def save(self, board, colour, score):
        while self.curr != self.top:
            self.boardStack.pop()
            self.attribStack.pop()
            self.top -= 1;
        self.boardStack.append(copy.deepcopy(board))
        self.attribStack.append((colour, copy.copy(score)))
        self.top += 1
        self.curr = self.top

    def setter(self, board, acolour, score):
        for i in range(len(self.boardStack[self.curr])):
            board[i] = copy.deepcopy(self.boardStack[self.curr][i])
        acolour[0] = self.attribStack[self.curr][0]
        score[0] = self.attribStack[self.curr][1][0]
        score[1] = self.attribStack[self.curr][1][1]

    def undo(self, board, acolour, score):
        if self.curr != -1:
            if self.curr > 0:
                self.curr -= 1
            self.setter(board, acolour, score)

    def redo(self, board, acolour, score):
        if self.curr < self.top:
            self.curr += 1
            self.setter(board, acolour, score)

# the contents of each tile on the board
class Tile:
    contents = BLANK
    score = 0

class Move:
    y = x = -1
    score = 0
    def __init__(self, y=-1, x=-1, s=0):
        self.y = y
        self.x = x
        self.score = s
    def __lt__(self, rhs):
        return self.score < rhs.score
    def __repr__(self):
        return "({},{},{})".format(self.y, self.x, self.score)

# simply turn black->white or white->black
def swap(colourIn):
    if colourIn == BLACK:
        return WHITE
    return BLACK

# walks a row/col/diag and counts piece that could be captured
def traceTiles(y, x, dy, dx, board, colour):
    score = 1
    while y >= 0 and y < 8 and x >=0 and x < 8 and board[y][x].contents == colour:
        y += dy
        x += dx
        score += 1
    if y < 0 or y >= 8 or x < 0 or x >= 8 or board[y][x].contents == BLANK:
        return 0
    return score 

# trace all neighbouts of a tile
def scoreTile(y, x, board, colour):
    other = swap(colour)
    for y1 in range(y-1, y+2):
        for x1 in range(x-1, x+2):
            if y1 == -1 or x1 == -1 or y1 == 8 or x1 == 8 or (y1 == y and x1 == x):
                continue
            if board[y1][x1].contents == other:
                dy, dx = y1-y, x1-x
                board[y][x].score += traceTiles(y1+dy, x1+dx, dy, dx, board, other)

# recursive scoring function and wide scoring test
def scoreBoard(board, colour, move, level):
    moveList = []
    urc = [BLANK]
    score = [0, 0]
    aur = UndoRedo()
    aur.save(board, colour, score)

    for y in range(8):
        for x in range(8):
            board[y][x].score = 0
            if board[y][x].contents == BLANK:
                scoreTile(y, x, board, colour)
                if board[y][x].score:
                    moveList.append(Move(y, x, board[y][x].score+advantage[y][x]))

    if moveList:
        moveList.sort()
        best = Move()
        tiles = 0
        initBest = False
        length = len(moveList)
        stdscr.refresh()
        length = int(length*(aiBreadth/5))+1
        moveList = moveList[-length:]
        if level+1 > aiDepth:
            move.__dict__ = moveList[-1].__dict__.copy()
            tiles = move.score - advantage[move.y][move.x]
        else:
            while moveList:
                amove = moveList.pop()
                cy, cx = stdscr.getyx()
                addPiece(amove.y, amove.x, board, colour)
                colour = swap(colour)
                omove = Move()
                scoreBoard(board, colour, omove, level+1)
                odd = (level % 2 != 0)
                if (not odd and amove.score - omove.score > best.score) or (odd and amove.score - omove.score < best.score) or not initBest:
                    best = copy.copy(amove)
                    tiles = best.score - advantage[best.y][best.x]
                    best.score -= omove.score
                    initBest = True
                aur.undo(board, urc, score) # reset
                colour = swap(colour)
            move.__dict__ = best.__dict__.copy()
        if level == 0:
            move.score = tiles
    else:
        move.y = -1

# turns captured tiles (white->black or black->white)
def setTraceTiles(y, x, dy, dx, board, colour):
    score, ox, oy, other = 0, x, y, swap(colour)
    while y >= 0 and y < 8 and x >=0 and x < 8 and board[y][x].contents == other:
        y += dy
        x += dx
        score += 1
    if y < 0 or y >= 8 or x < 0 or x >= 8 or board[y][x].contents == BLANK or score == 0:
        return
    x, y = ox, oy
    while y >= 0 and y < 8 and x >=0 and x < 8 and board[y][x].contents == other:
        board[y][x].contents = colour
        y += dy
        x += dx

# places a colour and sets neighbors/traces if captured
def addPiece(y, x, board, colour):
    board[y][x].contents = colour
    other = swap(colour)
    for y1 in range(y-1, y+2):
        for x1 in range(x-1, x+2):
            if y1 == -1 or x1 == -1 or y1 == 8 or x1 == 8 or (y1 == y and x1 == x):
                continue
            if board[y1][x1].contents == other:
                dy, dx = y1-y, x1-x
                setTraceTiles(y1, x1, dy, dx, board, colour)

# show score and who's turn and if it's human or AI
def drawScore(score, colour, status):
    y, x = int((screenY-(CELL_H*8))/2)-2, int(screenX/2)
    y, x = max(0, y), max(0, x)
    white = "White" if status[0] == 0 else "White (AI)"
    black = "Black" if status[1] == 0 else "Black (AI)"
    bstring = "%s: %3d" % (black, score[1])
    wstring = "%s: %3d" % (white, score[0])
    x -= int((len(wstring) + len(bstring) + 1) / 2)
    stdscr.addstr(y, x, bstring, curses.color_pair(CR_BLUE_CYAN if colour == WHITE else CR_BLACK_WHITE))
    stdscr.addstr(y, x + len(bstring) + 1, wstring, curses.color_pair(CR_BLUE_CYAN if colour == BLACK else CR_WHITE_BLUE))

# draws the 8x8 board and pieces
def drawBoard(board):
    y, x = int((screenY-(CELL_H*8))/2), int((screenX/2)-(CELL_W*8/2))
    y, x = max(0, y), max(0, x)
    for i in range(8):
        for j in range(8):
            stdscr.addstr(y+i*CELL_H, x+j*CELL_W, '[', curses.color_pair(CR_BLUE_CYAN))
            c = board[i][j].contents
            if c != BLANK and c != WHITE and c != BLACK:
                stdscr.addstr(1,0,"c is messed up.  It's {} at ({},{})".format(c,i,j))
                stdscr.refresh()
                stdscr.getch()
            col = curses.color_pair(CR_WHITE_CYAN)
            if c != BLANK:
                 if c == BLACK:
                    col = curses.color_pair(CR_BLACK_CYAN)
                    c = WHITE
            stdscr.addstr(y+i*CELL_H, x+j*CELL_W+1, c, col)
            stdscr.addstr(']', curses.color_pair(CR_BLUE_CYAN))
    stdscr.refresh()

# shows a non-interactive screen
def showMessage(message):
    stdscr.clear()
    length = 0
    for line in message:
        llen = len(line)
        if llen > length:
            length = llen

    y = max(0, int((screenY-len(message)) / 2))
    x = max(0, int((screenX-length) / 2))
    for line in message:
        stdscr.addstr(y, x, "{:{width}}".format(line, width=length), curses.color_pair(CR_WHITE_BLUE))
        y += 1
    stdscr.refresh()
    stdscr.getch()
    stdscr.clear()

# show the help screens
def drawHelp():
    helpText1 = [
        "",
        "                        Othello",
        "",
        " The goal in Othello is to trap pieces of the opposing ",
        " color between 2 of your pieces.  The \"line\" can be",
        " vertical, horizontal or diagonal.  Black moves first.",
        " The winner has the most pieces of their color on the",
        " board when there are no more possible moves.",
        " If there are no valid moves, use Pass in the menu.",
        "",
        " Keys:",
        "   Cursor keys - Move cursor around the board",
        "   Enter key   - Put down a piece in your color",
        "   ESC key     - Bring up the options menu",
        "   u           - Undo the last move",
        "   r           - Redo the next move (after undo)",
        "",
        "                                Press a key - Page 1/2",
        ""
    ]
    helpText2 = [
        "",
        "                        Othello",
        "",
        " In the settings menu are 2 AI options.  They do the  ",
        " following:",
        "",
        " Depth   - 0 through 8.  Controls how many levels deep ",
        "   the AI will think.  A depth of 0 is the AIs next",
        "   move.  1 is the opponent's counter move, 2 is the",
        "   AI counter to the counter, etc.  At level 8 and",
        "   breadth 5 the game is very slow on my PC.",
        " Breadth - 0 through 5.  Controls how many moved per",
        "   level the AI will consider.  0 is only the move",
        "   that yields the most pieces.  1 is 1/5th of all",
        "   possible, moves, 2 is 2/5ths, etc. 5 is all",
        "   possible moves for all levels up to Depth.",
        "",
        "                                Press a key - Page 2/2",
        ""
    ]
    showMessage(helpText1)
    showMessage(helpText2)

# just shows Game Over in red letters
def drawGameOver():
    string = "Game Over"
    y, x = int((screenY-(CELL_H*8))/2)+CELL_H*8+1, int(screenX/2)-int(len(string) / 2)
    stdscr.addstr(y, x, string, curses.color_pair(CR_RED_CYAN))

# move the cursor and on ENTER place a piece if it's a valid move
def getHumanPlay(board, colour, move):
    y, x = int((screenY-(CELL_H*8))/2), int((screenX/2)-(CELL_W*8/2) + CELL_W / 2)
    y, x = max(0, y), max(0, x)
    cx = cy = 0
    move.y = -1
    while True:
        stdscr.addstr(y, x, "")
        key = stdscr.getch()
        stdscr.refresh()
        if key in INPUT_COMMAND:
            return key
        elif key == curses.KEY_LEFT:
            if cx > 0:
                cx -= 1
                x -= CELL_W
        elif key == curses.KEY_RIGHT:
            if cx < 7:
                cx += 1
                x += CELL_W
        elif key == curses.KEY_UP:
            if cy > 0:
                cy -= 1
                y -= CELL_H
        elif key == curses.KEY_DOWN:
            if cy < 7:
                cy += 1
                y += CELL_H
        elif key in INPUT_SELECT and board[cy][cx].contents == BLANK:
                board[cy][cx].score = 0
                scoreTile(cy, cx, board, colour)
                if board[cy][cx].score > 0:
                    move.y = cy
                    move.x = cx
                    move.score = board[cy][cx].score#+advantage[cy][cx]
                    return curses.KEY_ENTER

# choose menu options; out 0 = play, 1 = pass, 2 = end match, 3 = quit
def getUserChoice(status, inGame):
    while True:
        stdscr.clear()
        menuItems = [" Single Player Game ", " Two Player Game", " Both Players AI", " AI Settings", " Help", " Quit"];
        if inGame:
            menuItems.append(" End Match")
            menuItems.append(" Pass")
        option = menu("Main Menu", menuItems, len(menuItems)+1, screenX, 
            "***** Python Othello V1.3 by Stefan Wessels, Jan. 2017.  ***** I wrote this game "
            "as a learning exercise - I wanted to learn Python and I used Othello as the way to "
            "learn.  Even though the AI is marginal, I think it is a success. ")

        if option == 0:
            option = menu(" Choose Your Color ", [" Play as Black", " Play as White", " Back"], 4, screenX, "Black goes first. *** ")
            if option == 0:
               status[0] = 1
               status[1] = 0
            elif option == 1:
               status[0] = 0
               status[1] = 1
            else:
                continue
            return 0

        elif option == 1:
            status[0] = status[1] = 0
            return 0
        elif option == 2:
            status[0] = status[1] = 1
            return 0
        elif option == 3:
            global aiBreadth, aiDepth
            maib = aiBreadth
            maid = aiDepth
            while option > 0:
                menuItems = ["Play with these settings", "Breadth: {}".format(maib), "Depth: {}".format(maid)]
                option = menu("Accept Settings", menuItems, 4, screenX, "***** See Help for an explanation of these values")
                if option == 1:
                    maib += 1
                    if maib > 5:
                        maib = 0
                if option == 2:
                    maid += 1
                    if maid > 8:
                        maid = 0
                if option == 0:
                    aiBreadth = maib
                    aiDepth = maid

        elif option == 4:
            drawHelp()
        elif option == 6:
            return 2
        elif option == 7:
            return 1
        else:
            option = menu("Quit", [" Absolutely ", " Maybe Not"], 3, screenX, "Are you sure? ")
            if option == 0:
                return 3
            else:
                continue

    return 0

# sets up the colours for curses, the background colour and clears the screen
def initScr(win):
    global stdscr, screenY, screenX
    stdscr = win
    if curses.has_colors():
        curses.init_pair(CR_BLUE_CYAN, curses.COLOR_BLUE, curses.COLOR_CYAN)
        curses.init_pair(CR_BLACK_CYAN, curses.COLOR_BLACK, curses.COLOR_CYAN)
        curses.init_pair(CR_WHITE_CYAN, curses.COLOR_WHITE, curses.COLOR_CYAN)
        curses.init_pair(CR_RED_CYAN, curses.COLOR_RED, curses.COLOR_CYAN);
        curses.init_pair(CR_YELLOW_BLUE, curses.COLOR_YELLOW, curses.COLOR_BLUE);
        curses.init_pair(CR_GREEN_BLUE, curses.COLOR_GREEN, curses.COLOR_BLUE);
        curses.init_pair(CR_WHITE_BLUE, curses.COLOR_WHITE, curses.COLOR_BLUE);
        curses.init_pair(CR_WHITE_GREEN, curses.COLOR_WHITE, curses.COLOR_GREEN);
        curses.init_pair(CR_BLACK_WHITE, curses.COLOR_BLACK, curses.COLOR_WHITE);

    stdscr.bkgd(curses.color_pair(CR_BLUE_CYAN))
    stdscr.clear()
    screenY, screenX = stdscr.getmaxyx()

# fills in the "advantage" grid and calls initScr
def init(win):
    global advantage, aiBreadth, aiDepth
    advantage = [
        [8, 0, 3, 2, 2, 3, 0, 8],
        [0, 0, 2, 0, 0, 2, 0, 0],
        [3, 2, 4, 3, 3, 4, 2, 3],
        [2, 0, 3, 0, 0, 3, 0, 2],
        [2, 0, 3, 0, 0, 3, 0, 2],
        [3, 2, 4, 3, 3, 4, 2, 3],
        [0, 0, 2, 0, 0, 2, 0, 0],
        [8, 0, 3, 2, 2, 3, 0, 8],
    ]
    aiBreadth = 0
    aiDepth = 0

    initScr(win)

# called from the curses.wrapper - main game loop
def main(win):

    init(win)

    quit = False

    while not quit:
        board = [[Tile() for x in range(8)] for y in range(8)] # [8][8] matrix
        board[3][3].contents = board[4][4].contents = WHITE
        board[3][4].contents = board[4][3].contents = BLACK
        gameOver, key, colour, score, status, urc = 0, 0, BLACK, [2, 2], [0, 0], [BLANK]
        move = Move()

        ur = UndoRedo()
        ur.save(board, colour, score)

        if getUserChoice(status, False):
            break

        while gameOver < 2:
            drawScore(score, colour, status)
            drawBoard(board)

            if status[ 0 if colour == WHITE else 1]:
                if status[0] == status[1] == 1:
                    key = stdscr.getch()
                scoreBoard(board, colour, move, 0)
            else:
                key = getHumanPlay(board, colour, move)

            if key == INPUT_BACKUP:
                key = getUserChoice(status, True)
                if key:
                    if key == 1:
                        colour = swap(colour)
                        continue
                    elif key == 3:
                        quit = True
                    break
                else:
                    continue
            elif key == INPUT_UNDO:
                # both undo & redo runs 2x, as it should, if one player is AI
                ur.undo(board, urc, score)
                colour = urc[0]
                continue
            elif key == INPUT_REDO:
                ur.redo(board, urc, score)
                colour = urc[0]
                continue

            if move.y != -1:
                gameOver = 0
                addPiece(move.y, move.x, board, colour)
                if colour == WHITE:
                    score[0] += 1 + move.score
                    score[1] -= move.score
                else:
                    score[1] += 1 + move.score
                    score[0] -= move.score

                ur.save(board, swap(colour), score)

                if score[0] == 0 or score[1] == 0 or score[0] + score[1] == 64:
                    drawBoard(board)
                    gameOver = 2
            else:
                gameOver += 1

            colour = swap(colour)

        else:
            drawScore(score, BLANK, status)
            drawGameOver()
            stdscr.getch()

# inits the terminal, calls the game and cleans up the terminal again
curses.wrapper(main)
