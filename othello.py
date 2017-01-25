"""
Othello, using curses, by Stefan Wessels.
Versions:
    V1.0 - 11 Jan 2017 - Initial Release - Windows only.
    V1.1 - 12 Jan 2017 - Mac and Linux support.
    V1.2 - 12 Jan 2017 - ESC brings up in-game menu.
    V1.3 - 13 Jan 2017 - Added help and Undo/Redo. Made board look nicer.
    V1.4 - 14 Jan 2017 - Added recursive AI and settings for this AI.
    V1.4a- 15 Jan 2017 - Cleanup and fixed a very silly AI bug
    V1.5 - 24 Jan 2017 - Put in new menu system.  Affects only AI Settings
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

INPUT_MOTION        = [curses.KEY_UP, curses.KEY_DOWN]
INPUT_SELECT        = [curses.KEY_ENTER, 10, 13]
INPUT_BACKUP        = 27 # ESC key
INPUT_UNDO          = 117 # u key
INPUT_REDO          = 114 # r key
INPUT_COMMAND       = [INPUT_BACKUP, INPUT_UNDO, INPUT_REDO]
SCROLL_SPEED        = 0.15
BLANK               = ' '
WHITE               = 'O'
BLACK               = 'X'
CELL_W              = 3
CELL_H              = 1

CR_BLUE_CYAN        = 1
CR_BLACK_CYAN       = 2
CR_WHITE_CYAN       = 3
CR_RED_CYAN         = 4
CR_YELLOW_BLUE      = 5
CR_GREEN_BLUE       = 6
CR_WHITE_BLUE       = 7
CR_WHITE_GREEN      = 8
CR_BLACK_WHITE      = 9

# colours the menu system uses
MENU_CLR_TITLE      = 7
MENU_CLR_ITEMS      = 7
MENU_CLR_FOOTER     = 6
MENU_CLR_SELECT     = 8
MENU_CLR_DISABLED   = 4

# contains all elements to make/draw a menu
class MenuItems:
    def __init__(self, *args, **kwargs):
        self.y = kwargs.get('y', None)
        self.x = kwargs.get('x',None)
        self.width = kwargs.get('width',None) 
        self.height = kwargs.get('height',None) 
        self.title = kwargs.get('title', None)
        self.items = kwargs.get('items', None)
        self.callbacks = kwargs.get('callbacks', None)
        self.states = kwargs.get('states', None)
        self.footer = kwargs.get('footer', None)
        self.header_height = kwargs.get('header_height', 2)
        self.footer_height = kwargs.get('footer_height', 2)
    def __repr__(self):
        return "[y:{} x:{} w:{} h:{}]".format(self.y, self.x, self.width, self.height)

# shows a menu and returns user choice
def menu(menuItems):
    # gets lenth of longest item in array "items"
    def _maxItemLength(items):
        maxItemLen = 0
        for item in items:
            maxItemLen = max(maxItemLen, len(item))
        return maxItemLen

    # finds the next item in "status" that has a 1 from selectedItem in direction (1 or -1)
    # returns -1 or len(menuItems.states) if it runs off the end of the list
    def _next_item(menuItems, selectedItem, direction):
        selectedItem += direction
        # always just next if there are no states
        if not menuItems.states:
            return selectedItem
        numMenuStates = len(menuItems.states)
        while True:
            if selectedItem >= numMenuStates or selectedItem < 0:
                return selectedItem
            if menuItems.states[selectedItem]:
                return selectedItem
            selectedItem += direction

    # Took this out as it requires Python 3.x
    # # you can call menu with an array only
    # if type(menuItems) is not MenuItems:
    #     if type(menuItems) is list:
    #         menuItems = MenuItems(items=menuItems)
    #     else:
    #         raise Exception("menuItems must be of class MenuItem or a list not {}".format(type(menuItems)))

    # make sure there's enough screen to display at leaset line with the selectors (><) and 1 char
    sy, sx = stdscr.getmaxyx()
    if sy < 1 or sx < 3:
        raise Exception("screen too small")

    # create placeholder y/x locations
    _y = 0 if menuItems.y is None else menuItems.y
    _x = 0 if menuItems.x is None else menuItems.x

    # make sure the top left edge of the menu is on-screen
    if _y < 0 or _y >= sy or _x < 0 or _x > sx-3:
        raise Exception("menu top/left too off-screen")

    # get height of menu
    numMenuItems = len(menuItems.items)
    numMenuHeaders = menuItems.header_height if menuItems.title is not None else 0
    numMenuFooters = menuItems.footer_height if menuItems.footer is not None else 0

    # get length of footer
    footerLength = 0 if not menuItems.footer else len(menuItems.footer)

    # now calc height if not provided
    if menuItems.height is None:
        menuItems.height = numMenuItems + numMenuHeaders + numMenuFooters;
    # make sure height fits on screen
    if _y + menuItems.height > sy - 1:
        menuItems.height = sy - _y - 1

    # calc width if not provided
    if menuItems.width is None:
        titleLength = 0 if menuItems.title is None else len(menuItems.title)
        menuItems.width = max(_maxItemLength(menuItems.items), titleLength)
    # make sure it fits on the screen
    if _x + menuItems.width > sx - 2:
        menuItems.width = sx - _x - 2

    # centre the menu if y or x was not provided
    if menuItems.y is None:
        menuItems.y = max(0,int((sy-menuItems.height)/2))
    if menuItems.x is None:
        menuItems.x = max(0,int((sx-(menuItems.width+2))/2))

    # calculate how many items can be shown
    numVisibleItems = menuItems.height - (numMenuHeaders + numMenuFooters)

    # show 1st item as selected
    selectedItem = _next_item(menuItems, -1, 1)
    if selectedItem > numMenuItems:
        raise Exception("No enabled menu items")
    topItem = 0
    if selectedItem - topItem >= numVisibleItems:
        topItem = selectedItem - numVisibleItems + 1
    # start selected item from 1st character
    itemOffset = 0
    # if selected item has to scroll, scroll it left
    itemDirection = 1
    # start footer from 1st character
    footerOffset = 0

    # if none, then throw exception
    if numVisibleItems < 1:
        raise Exception("menu too short to show any items")

    # init the line (y) variable
    line = menuItems.y

    # show the title if there is one to be shown
    if menuItems.title is not None:
        stdscr.addstr(line, menuItems.x, " {:^{width}} ".format(menuItems.title[:menuItems.width], width=menuItems.width), curses.color_pair(MENU_CLR_TITLE))
        line += 1
        while line - menuItems.y < numMenuHeaders:
            stdscr.addstr(line, menuItems.x, " " * (2 + menuItems.width), curses.color_pair(MENU_CLR_FOOTER))
            line += 1

        # now the menu starts below the title
        menuItems.y = line

    # get time for scrolling putposes
    startTime = time.time()
    # go into the main loop
    while True:
        # get time now to calculate elapsed time
        thisTime = time.time()
        # start at the top to draw
        line = menuItems.y

        # show the visible menu items, highlighting the selected item
        for i in range(topItem, min(numMenuItems,topItem+numVisibleItems)):
            display = " {:{width}} "
            if menuItems.states is None or i >= len(menuItems.states) or menuItems.states[i]:
                color = curses.color_pair(MENU_CLR_ITEMS)
            else:
                color = curses.color_pair(MENU_CLR_DISABLED)
            if i == selectedItem:
                display = ">{:{width}}<"
                color = curses.color_pair(MENU_CLR_SELECT)
                # if the item is longer than the menu width, bounce the item back and forth in the menu display
                if thisTime-startTime > SCROLL_SPEED:
                    displayLength = len(menuItems.items[i])
                    if displayLength > menuItems.width:
                        itemOffset += itemDirection
                        # swap scroll itemDirection but hold for one frame at either end
                        if itemOffset == 0 or itemOffset > displayLength - menuItems.width:
                            if itemDirection:
                                itemDirection = 0
                            elif itemOffset == 0:
                                itemDirection = 1
                            else:
                                itemDirection = -1
            # put ^ or V on the top/bottom lines if there are more options but keep > on selected
            if i == topItem and topItem != 0:
                display = display[:len(display)-1]+"^"
            elif i == topItem+numVisibleItems-1 and i != numMenuItems-1:
                display = display[:len(display)-1]+"v"
            
            # format the line for display
            if i == selectedItem:
                display = display.format(menuItems.items[i][itemOffset:itemOffset+menuItems.width], width=menuItems.width)
            else:
                display = display.format(menuItems.items[i][:menuItems.width], width=menuItems.width)

            # show the item
            stdscr.addstr(line, menuItems.x, display, color)
            line += 1

        # pad out the footer area, if there is one
        while line < menuItems.y + numVisibleItems + numMenuFooters:
            stdscr.addstr(line, menuItems.x, " " * (2 + menuItems.width), curses.color_pair(MENU_CLR_FOOTER))
            line += 1

        # display the footer if there is one
        if menuItems.footer is not None:
            stdscr.addstr(line, menuItems.x, " " + menuItems.footer[footerOffset:footerOffset+menuItems.width], curses.color_pair(MENU_CLR_FOOTER))
            remain = footerLength-footerOffset
            while remain < menuItems.width:
                string = menuItems.footer[:menuItems.width-remain]
                stdscr.addstr(line, menuItems.x+1+remain, string, curses.color_pair(MENU_CLR_FOOTER))
                remain += len(string)
            stdscr.addstr(" ", curses.color_pair(MENU_CLR_FOOTER))

        # make it all visible
        stdscr.refresh()

        # calculate a new scroll position for the footer
        if thisTime-startTime > SCROLL_SPEED:
            footerOffset += 1
            startTime = time.time()
            if footerOffset == footerLength:
                footerOffset = 0

        # test keys and deal with key presses
        keyPressed = 0
        if windows:
            keyPressed = msvcrt.kbhit()
        else:
            dr, dw, de = select.select([sys.stdin], [], [], 0)
            if not dr == []:
                keyPressed = 1

        if keyPressed:
            key = stdscr.getch()
            # this allows callbaks to "press keys"
            while key:
                # cursor key up/down
                if key in INPUT_MOTION:
                    itemOffset = 0
                    itemDirection = 1
                    # cursor up
                    if key == curses.KEY_DOWN:
                        i = _next_item(menuItems, selectedItem, 1)
                        if i >= numMenuItems:
                            i = _next_item(menuItems, -1, 1)
                            if i >= numMenuItems:
                                raise Exception("No enabled menu items")
                            topItem = 0
                        if i - topItem >= numVisibleItems:
                            topItem = i - numVisibleItems + 1
                        selectedItem = i
                    # cursor down
                    if key == curses.KEY_UP:
                        i = _next_item(menuItems, selectedItem, -1)
                        if i < 0:
                            i = _next_item(menuItems, numMenuItems, -1)
                            if i < 0:
                                raise Exception("No enabled menu items")
                            topItem = max(0,numMenuItems - numVisibleItems)
                        if topItem > i:
                            topItem = i
                        selectedItem = i
                    key = None

                # ENTER key
                elif key in INPUT_SELECT:
                    if menuItems.callbacks is not None:
                        # make sure there's a callback and that it's a function
                        if selectedItem < len(menuItems.callbacks) and callable(menuItems.callbacks[selectedItem]):
                            key = menuItems.callbacks[selectedItem](menuItems, selectedItem)
                            numMenuItems = len(menuItems.items)
                    # test again - The callback may have altered the key
                    if key in INPUT_SELECT:
                        return selectedItem

                # BACKUP (normally ESC) breaks out of the menu
                elif key == INPUT_BACKUP:
                    return -1
                # ignore all other keys
                else:
                    break

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

# keeps track of x,y and potential score
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
        length = max(1,int(length*(aiBreadth/5)))
        moveList = moveList[-length:]
        if level+1 > aiDepth:
            move.__dict__ = moveList[-1].__dict__.copy()
            tiles = move.score - advantage[move.y][move.x]
        else:
            aur = UndoRedo()
            score = [0, 0]
            aur.save(board, colour, score)
            urc = [BLANK]
            while moveList:
                amove = moveList.pop()
                addPiece(amove.y, amove.x, board, colour)
                colour = swap(colour)
                omove = Move()
                scoreBoard(board, colour, omove, level+1)
                if amove.score - omove.score > best.score or not initBest:
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
                    move.score = board[cy][cx].score
                    return curses.KEY_ENTER

# choose menu options; out 0 = play, 1 = pass, 2 = end match, 3 = quit
def getUserChoice(status, inGame):
    def upvar(menuItems, selectedItem):
        if selectedItem == 1:
            menuItems.aiBreadth += 1
            if menuItems.aiBreadth > 5:
                menuItems.aiBreadth = 0
            menuItems.items[1] = "Breadth: {}".format(menuItems.aiBreadth)
        else:
            menuItems.aiDepth += 1
            if menuItems.aiDepth > 8:
                menuItems.aiDepth = 0
            menuItems.items[2] = "Depth: {}".format(menuItems.aiDepth)

    while True:
        stdscr.clear()
        menuItems = MenuItems(
            title = "Main Menu",
            items = [" Single Player Game ", " Two Player Game", " Both Players AI", " AI Settings", " Help", " Quit"],
            footer = "***** Python Othello V1.4a by Stefan Wessels, Jan. 2017.  ***** I wrote this game "
                    "as a learning exercise - I wanted to learn Python and I used Othello as the way to "
                    "learn.  Even though the AI is marginal, I think it is a success. "
            )
        if inGame:
            menuItems.items.append(" End Match")
            menuItems.items.append(" Pass")
        option = menu(menuItems)
        stdscr.clear()

        if option == 0:
            menuItems = MenuItems(
                title = " Choose Your Color ", 
                items = [" Play as Black", " Play as White", " Back"], 
                footer = "*** Black goes first. "
                )
            option = menu(menuItems)
            stdscr.clear()
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
            while option > 0:
                menuItems = MenuItems(
                    title = "Accept Settings",
                    items = ["Play with these settings", "Breadth: {}".format(aiBreadth), "Depth: {}".format(aiDepth)],
                    footer = "***** See Help for an explanation of these values ",
                    callbacks = [None, upvar, upvar]
                    )
                menuItems.aiBreadth = aiBreadth
                menuItems.aiDepth = aiDepth
                option = menu(menuItems)
                stdscr.clear()
                if option == 0:
                    aiBreadth = menuItems.aiBreadth
                    aiDepth = menuItems.aiDepth

        elif option == 4:
            drawHelp()
        elif option == 6:
            return 2
        elif option == 7:
            return 1
        else:
            menuItems = MenuItems(
                title = "Quit", 
                items = [" Absolutely ", " Maybe Not"], 
                footer = "Are you sure? "
                )
            option = menu(menuItems)
            stdscr.clear()
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
                if status[0] != status [1]:
                    ur.undo(board, urc, score)
                ur.undo(board, urc, score)
                colour = urc[0]
                continue
            elif key == INPUT_REDO:
                if status[0] != status [1]:
                    ur.redo(board, urc, score)
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
