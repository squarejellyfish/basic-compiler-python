import enum
import sys

def eprint(*args, **kwargs):
    print(*args, file=sys.stderr, **kwargs)

class Lexer:
    def __init__(self, source, sourceName):
        self.source: str = source + '\n' # Source code to lex as a string. Append a newline to simplify lexing/parsing the last token/statement.
        self.curChar: str = ''   # Current character in the string.
        self.curPos: int = -1    # Current position in the string.
        self.curLine: int = 1
        self.linePos: int = 0
        self.sourceName = sourceName
        self.nextChar()

    # Process the next character.
    def nextChar(self):
        if self.curChar == '\n':
            self.curLine += 1
            self.linePos = 1
        self.curPos += 1
        self.linePos += 1
        if self.curPos >= len(self.source):
            self.curChar = '\0'
        else:
            self.curChar = self.source[self.curPos]

    # Return the lookahead character.
    def peek(self):
        if self.curPos + 1 >= len(self.source):
            return '\0'

        return self.source[self.curPos + 1]

    # Invalid token found, print error message and exit.
    def abort(self, message):
        eprint(f"{self.sourceName}:{self.curLine}:{self.linePos} Lexing error. " + message)
        sys.exit(69)
		
    # Skip whitespace except newlines, which we will use to indicate the end of a statement.
    def skipWhitespace(self):
        while self.curChar == ' ' or self.curChar == '\t' or self.curChar == '\r':
            self.nextChar()
		
    # Skip comments in the code.
    def skipComment(self):
        if self.curChar == '#':
            while self.curChar != '\n':
                self.nextChar()

    # Return the next token.
    def getToken(self):
        self.skipWhitespace()
        self.skipComment()
        token = None

        # Check the first character of this token to see if we can decide what it is.
        # If it is a multiple character operator (e.g., !=), number, identifier, or keyword then we will process the rest.
        if self.curChar == '+':
            token = Token(self.curChar, TokenType.PLUS, self.curLine, self.linePos)
        elif self.curChar == '-':
            token = Token(self.curChar, TokenType.MINUS, self.curLine, self.linePos)
        elif self.curChar == '*':
            token = Token(self.curChar, TokenType.ASTERISK, self.curLine, self.linePos)
        elif self.curChar == '/':
            token = Token(self.curChar, TokenType.SLASH, self.curLine, self.linePos)
        elif self.curChar == '=':
            # Check if this token is '=' or '==' by peeking the next char
            if self.peek() == '=':
                lastChar = self.curChar
                self.nextChar()
                token = Token(lastChar + self.curChar, TokenType.EQEQ, self.curLine, self.linePos)
            else:
                token = Token(self.curChar, TokenType.EQ, self.curLine, self.linePos)
        elif self.curChar == '>':
            # Check whether this is token is > or >=
            if self.peek() == '=':
                lastChar = self.curChar
                self.nextChar()
                token = Token(lastChar + self.curChar, TokenType.GTEQ, self.curLine, self.linePos)
            else:
                token = Token(self.curChar, TokenType.GT, self.curLine, self.linePos)
        elif self.curChar == '<':
                # Check whether this is token is < or <=
                if self.peek() == '=':
                    lastChar = self.curChar
                    self.nextChar()
                    token = Token(lastChar + self.curChar, TokenType.LTEQ, self.curLine, self.linePos)
                else:
                    token = Token(self.curChar, TokenType.LT, self.curLine, self.linePos)
        elif self.curChar == '!':
            if self.peek() == '=':
                lastChar = self.curChar
                self.nextChar()
                token = Token(lastChar + self.curChar, TokenType.NOTEQ, self.curLine, self.linePos)
            else:
                self.abort("Expected !=, got !" + self.peek())
        elif self.curChar == '"':
            self.nextChar()
            startPos = self.curPos

            while self.curChar != '"':
                if self.curChar == '\r' or self.curChar == '\n' or self.curChar == '\t' or self.curChar == '\\' or self.curChar == '%':
                    self.abort("Illegal character in string: " + self.curChar)
                self.nextChar()

            text = self.source[startPos:self.curPos]
            token = Token(text, TokenType.STRING, self.curLine, self.linePos)
        elif self.curChar == '(':
            token = Token(self.curChar, TokenType.LPARENT, self.curLine, self.linePos) 
        elif self.curChar == ')':
            token = Token(self.curChar, TokenType.RPARENT, self.curLine, self.linePos) 
        elif self.curChar.isdigit():
            # Assume this is a number, if not we abort
            # Get all consecutive digits and decimal
            startPos = self.curPos
            while self.peek().isdigit():
                self.nextChar()
            if self.peek() == '.': # decimal
                self.nextChar()

                if not self.peek().isdigit():
                    self.abort("Illegal character in number: " + self.peek())
                while self.peek().isdigit():
                    self.nextChar()

            text = self.source[startPos:self.curPos + 1]
            token = Token(text, TokenType.NUMBER, self.curLine, self.linePos)
        elif self.curChar.isalpha():
            startPos = self.curPos
            while self.peek().isalpha():
                self.nextChar()

            text = self.source[startPos:self.curPos + 1]
            iskeyword, kind = Token.isKeyword(text)
            if iskeyword:
                token = Token(text, kind, self.curLine, self.linePos)
            else:
                token = Token(text, TokenType.IDENT, self.curLine, self.linePos)
        elif self.curChar == '\n':
            token = Token(self.curChar, TokenType.NEWLINE, self.curLine, self.linePos)
        elif self.curChar == '\0':
            token = Token(self.curChar, TokenType.EOF, self.curLine, self.linePos)
        else:
            # Unknown token!
            self.abort("Unknown token: " + self.curChar)
			
        self.nextChar()
        return token

class Token:
    def __init__(self, tokenText, tokenKind, curLine=0, linePos=0):
        self.text = tokenText   # The token's actual text. Used for identifiers, strings, and numbers.
        self.kind = tokenKind   # The TokenType that this token is classified as.
        self.curLine = curLine
        self.linePos = linePos

    @staticmethod
    def isKeyword(text):
        for kind in TokenType:
            if kind.value >= 100 and kind.value < 200:
                # special case (reserved words)
                if kind is TokenType.if_ and text == str(kind.name)[:-1]:
                    return (True, kind)
                elif kind is TokenType.while_ and text == str(kind.name)[:-1]:
                    return (True, kind)
                elif kind is TokenType.and_ and text == str(kind.name)[:-1]:
                    return (True, kind)
                elif kind is TokenType.or_ and text == str(kind.name)[:-1]:
                    return (True, kind)
                elif kind is TokenType.not_ and text == str(kind.name)[:-1]:
                    return (True, kind)
                elif kind is TokenType.else_ and text == str(kind.name)[:-1]:
                    return (True, kind)
                # other case
                elif kind.name == text:
                    return (True, kind)
        return (False, None)

# TokenType is our enum for all the types of tokens.
class TokenType(enum.Enum):
    EOF = -1
    NEWLINE = 0
    NUMBER = 1
    IDENT = 2
    STRING = 3
    LPARENT = 4
    RPARENT = 5
    # Keywords.
    label = 101
    goto = 102
    print = 103
    input = 104
    let = 105
    if_ = 106
    then = 107
    end = 108
    while_ = 109
    do = 110
    and_ = 111
    or_ = 112
    not_ = 113
    else_ = 114
    # Operators.
    EQ = 201  
    PLUS = 202
    MINUS = 203
    ASTERISK = 204
    SLASH = 205
    EQEQ = 206
    NOTEQ = 207
    LT = 208
    LTEQ = 209
    GT = 210
    GTEQ = 211
