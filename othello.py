"""
Othello, using curses, by Stefan Wessels.
Versions:
  V1.0 - 11 Jan 2017 - Initial Release - Windows only.
  V1.1 - 12 Jan 2017 - Made this also work in Mac and Linux.  Some comments added.
  V1.2 - 12 Jan 2017 - ESC brings up menu in-game and you can change options & pass
"""

import curses
import time

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
SCROLL_SPEED    = 0.15
BLANK           = ' '
WHITE           = 'O'
BLACK           = 'X'
score_y         = 1
board_y         = score_y + 2
gameover_y      = board_y + 2 + 16

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

    sy = int(max(0, screenY / 2 - (menuHeight / 2) - 1))
    sx = int(max(0, screenX / 2 - (maxLen / 2) - 1))
    maxLen = int(min(maxWidth-2, maxLen))

    scrollIndex = 0
    scrollLength = len(scroller)
    
    stdscr.addstr(sy,sx, ' {:^{width}} '.format(title[:maxLen], width=maxLen), curses.color_pair(CR_YELLOW_BLUE))
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
        stdscr.addstr(sy+i,sx, '>{:{width}}<'.format(menuItems[i][:maxLen], width=maxLen), curses.color_pair(CR_WHITE_GREEN))
        keyPressed = 0
        if windows:
            keyPressed = msvcrt.kbhit()
        else:
            dr,dw,de = select.select([sys.stdin], [], [], 0)
            if not dr == []:
                keyPressed = 1
        if keyPressed:
            key = stdscr.getch()
            if key in INPUT_MOTION:
                stdscr.addstr(sy+i,sx, ' {:{width}} '.format(menuItems[i][:maxLen], width=maxLen), curses.color_pair(CR_WHITE_BLUE))
                if key == curses.KEY_UP:
                    i -= 1
                    if i < 0:
                        i = numMenuItems-1
                elif key == curses.KEY_DOWN:
                    i += 1
                    if numMenuItems == i:
                        i = 0
        
        stdscr.addstr(sy+menuHeight, sx, " " + scroller[scrollIndex:scrollIndex+maxLen], curses.color_pair(CR_GREEN_BLUE))
        remain = scrollLength - scrollIndex
        while remain < maxLen:
            string = scroller[:maxLen-remain]
            stdscr.addstr(sy+menuHeight,sx+1+remain, string, curses.color_pair(CR_GREEN_BLUE))
            remain += len(string)
        stdscr.addstr(" ", curses.color_pair(CR_GREEN_BLUE))
        stdscr.refresh()

        if time.time() - start > SCROLL_SPEED:
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

# the contents of each tile on the board
class Tile:
    contents = BLANK
    score = 0

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

# check all tiles to see which move captures most tiles/is most desirable
def scoreBoard(board, colour, best):
    for y in range(8):
        for x in range(8):
            board[y][x].score = 0
            if board[y][x].contents == BLANK:
                scoreTile(y, x, board, colour)
                if board[y][x].score and board[y][x].score + advantage[y][x] > best[2]:
                    best[0] = y
                    best[1] = x
                    best[2] = board[y][x].score + advantage[y][x]

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
    y, x = score_y, int(screenX / 2)
    white = "White" if status[0] == 0 else "White (AI)"
    black = "Black" if status[1] == 0 else "Black (AI)"
    bstring = "%s: %3d" % (black, score[1])
    wstring = "%s: %3d" % (white, score[0])
    x -= int((len(wstring) + len(bstring) + 1) / 2)
    stdscr.addstr(y, x, bstring, curses.color_pair(CR_BLUE_CYAN if colour == WHITE else CR_BLACK_WHITE))
    stdscr.addstr(y, x + len(bstring) + 1, wstring, curses.color_pair(CR_BLUE_CYAN if colour == BLACK else CR_WHITE_BLUE))

# drwas the 8x8 board and pieces
def drawBoard(board):
    y, x = board_y, int(screenX / 2) - 8 # 8 is .5 * board_width
    for i in range(8):
        stdscr.addstr(y,x,'+-'*8+'+', curses.color_pair(CR_BLUE_CYAN))
        y += 1
        for j in range(8):
            stdscr.addstr(y,x+j*2,'|', curses.color_pair(CR_BLUE_CYAN))
            c = board[i][j].contents
            col = curses.color_pair(CR_WHITE_CYAN)
            if c != BLANK:
                 if c == BLACK:
                    col = curses.color_pair(CR_BLACK_CYAN)
                    c = WHITE
            stdscr.addstr(y,x+j*2+1,c, col )
        stdscr.addstr('|', curses.color_pair(CR_BLUE_CYAN))
        y += 1
    stdscr.addstr(y,x,'+-'*8+'+', curses.color_pair(CR_BLUE_CYAN))
    stdscr.refresh()

# just shows Game Over in red letters
def drawGameOver():
    string = "Game Over"
    y, x = gameover_y, int(screenX / 2) - int(len(string) / 2)
    stdscr.addstr(y, x, string, curses.color_pair(CR_RED_CYAN))

# move the cursor and on ENTER place a piece if it's a valid move
def getHumanPlay(board, colour, best):
    y, x = board_y+1, int(screenX / 2) - 8 + 1
    cx = cy = 0
    best[0] = -1
    while True:
        stdscr.addstr(y,x,"")
        key = stdscr.getch()
        if key == INPUT_BACKUP:
            return key
        elif key == curses.KEY_LEFT:
            if cx > 0:
                cx -= 1
                x -= 2
        elif key == curses.KEY_RIGHT:
            if cx < 7:
                cx += 1
                x += 2
        elif key == curses.KEY_UP:
            if cy > 0:
                cy -= 1
                y -= 2
        elif key == curses.KEY_DOWN:
            if cy < 7:
                cy += 1
                y += 2
        elif key in INPUT_SELECT and board[cy][cx].contents == BLANK:
                board[cy][cx].score = 0
                scoreTile(cy, cx, board, colour)
                if board[cy][cx].score > 0:
                    best[0] = cy
                    best[1] = cx
                    best[2] = board[cy][cx].score + advantage[cy][cx]
                    return curses.KEY_ENTER

# choose menu options; out 0 = play, 1 = pass, 2 = end match, 3 = quit
def getUserChoice(status, inGame):
    while True:
        stdscr.clear()
        menuItems = [" Single Player Game ", " Two Player Game", " Both Players AI", " Quit"];
        if inGame:
            menuItems.append(" End Match")
            menuItems.append(" Pass")
        option = menu("Main Menu", menuItems, len(menuItems)+1, screenX, 
            "****** Python Othello V1.2 by Stefan Wessels, Jan. 2017.  Cursor keys to move cursor.  "
            "Enter to place a piece.  ESC to bring up the menu.  I wrote this game over 2 days as a "
            "learning exercise - I wanted to learn Python and I wanted to make an Othello game.  Even "
            "though the AI is marginal, I think the whole thing is a pretty big success! ")

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
        elif option == 2:
            status[0] = status[1] = 1
        elif option == 4:
            return 2
        elif option == 5:
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
    global advantage
    advantage = [
        [8,0,3,2,2,3,0,8],
        [0,0,2,0,0,2,0,0],
        [3,2,4,3,3,4,2,3],
        [2,0,3,0,0,3,0,2],
        [2,0,3,0,0,3,0,2],
        [3,2,4,3,3,4,2,3],
        [0,0,2,0,0,2,0,0],
        [8,0,3,2,2,3,0,8],
    ]
    initScr(win)

# called from the curses.wrapper - main game loop
def main(win):

    init(win)

    quit = False

    while not quit:
        board = [[Tile() for x in range(8)] for y in range(8)] # [8][8] matrix
        board[3][3].contents = board[4][4].contents = WHITE
        board[3][4].contents = board[4][3].contents = BLACK
        gameOver, key, colour, score, status = 0, 0, BLACK, [2, 2], [0, 0]

        if getUserChoice(status, False):
            break

        while gameOver < 2:
            drawScore(score, colour, status)
            drawBoard(board)

            best = [-1, -1, 0]
            if status[ 0 if colour == WHITE else 1]:
                scoreBoard(board, colour, best)
                if status[0] == status[1] == 1:
                    key = stdscr.getch()
            else:
                key = getHumanPlay(board, colour, best)

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

            if best[0] != -1:
                gameOver = 0
                addPiece(best[0], best[1], board, colour)
                if colour == WHITE:
                    score[0] += 1 + best[2] - advantage[best[0]][best[1]]
                    score[1] -= best[2] - advantage[best[0]][best[1]]
                else:
                    score[1] += 1 + best[2] - advantage[best[0]][best[1]]
                    score[0] -= best[2] - advantage[best[0]][best[1]]
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
