import sys
from emit import Emitter
from lex import *

"""
TODO: FOR, WHILE loop, for turing completeness, best is just translate C functions to here
"""

# Parser object keeps track of current token and checks if the code matches the grammar.
class Parser:
    def __init__(self, lexer, emitter):
        self.lexer: Lexer = lexer
        self.emitter: Emitter = emitter

        self.symbols = set()
        self.labelsDeclared = set()
        self.labelsGotoed = set()

        self.curToken = None
        self.peekToken = None
        self.nextToken()
        self.nextToken() # Call twice ot init curToken and peekToken

    # Return true if the current token matches.
    def checkToken(self, kind):
        return kind == self.curToken.kind

    # Return true if the next token matches.
    def checkPeek(self, kind):
        return kind == self.peekToken.kind

    # Try to match current token. If not, error. Advances the current token.
    def match(self, kind):
        if not self.checkToken(kind):
            self.abort(f"Expected {kind.name}, got {self.curToken.text}")
        self.nextToken()

    # Advances the current token.
    def nextToken(self):
        self.curToken = self.peekToken
        self.peekToken = self.lexer.getToken()

    def abort(self, message):
        eprint(f"{self.lexer.sourceName}:{self.curToken.curLine}:{self.curToken.linePos} Error: " + message) 
        sys.exit(69)

    def isComparisonOp(self):
        return self.checkToken(TokenType.GT) or self.checkToken(TokenType.GTEQ) or self.checkToken(TokenType.LT) or self.checkToken(TokenType.LTEQ) or self.checkToken(TokenType.EQEQ) or self.checkToken(TokenType.NOTEQ)

    # program ::= {statement}
    def program(self):
        self.emitter.headerLine("#include <stdio.h>")
        self.emitter.headerLine("int main(void) {")
        print("PROGRAM")

        # Strip newlines at start
        while self.checkToken(TokenType.NEWLINE):
            self.nextToken()

        # Parse all the statements
        while not self.checkToken(TokenType.EOF):
            self.statement()

        self.emitter.emitLine("return 0;")
        self.emitter.emitLine("}")

        # Check that each label referenced in a GOTO is declared.
        for label in self.labelsGotoed:
            if label not in self.labelsDeclared:
                self.abort("Attempting to GOTO to undeclared label: " + label)

    def statement(self):
        # Check first token to see which statement

        # PRINT (expr | string)
        if self.checkToken(TokenType.print):
            print("STATEMENT-PRINT")
            self.nextToken()

            if self.checkToken(TokenType.STRING): # just string
                self.emitter.emitLine(f'printf("{self.curToken.text}\\n");')
                self.nextToken()
            else: # else it's a expr
                # Expect an expression and print the result as a float.
                self.emitter.emit("printf(\"%" + ".2f\\n\", (float)(")
                self.expression()
                self.emitter.emitLine("));")
        # IF comparison THEN {statement} ENDIF
        elif self.checkToken(TokenType.if_):
            print("STATEMENT-IF")
            self.emitter.emit("if(")
            self.nextToken()
            self.comparison()

            self.match(TokenType.then)
            self.nl()
            self.emitter.emitLine("){") 

            while not self.checkToken(TokenType.end):
                # ELSE IF comparison THEN {statement}
                if self.checkToken(TokenType.else_) and self.peekToken.kind is TokenType.if_:
                    print("STATEMENT-ELSEIF")
                    self.emitter.emit("}else if(")
                    self.nextToken()
                    self.nextToken()

                    self.comparison()

                    self.match(TokenType.then)
                    self.nl()

                    self.emitter.emitLine("){")
                # ELSE
                elif self.checkToken(TokenType.else_):
                    print("STATEMENT-ELSE")
                    self.nextToken()
                    self.nl()
                    self.emitter.emitLine("}else{")

                self.statement()

            self.match(TokenType.end)
            self.emitter.emitLine("}") 
        # WHILE comparison REPEAT nl {statement nl} ENDWHILE nl
        elif self.checkToken(TokenType.while_):
            print("STATEMENT-WHILE")
            self.emitter.emit("while (")
            self.nextToken()
            self.comparison()

            self.match(TokenType.do)
            self.nl()
            self.emitter.emitLine("){")

            while not self.checkToken(TokenType.end):
                self.statement()

            self.match(TokenType.end)
            self.emitter.emitLine("}")
        # "LABEL" ident
        elif self.checkToken(TokenType.label):
            print("STATEMENT-LABEL")
            self.nextToken()

            # Check if this label already exist
            if self.curToken.text in self.labelsDeclared:
                self.abort(f"Label already exists: {self.curToken.text}")
            self.labelsDeclared.add(self.curToken.text)

            self.emitter.emitLine(self.curToken.text + ':')
            self.match(TokenType.IDENT)
        # "GOTO" ident
        elif self.checkToken(TokenType.goto):
            print("STATEMENT-GOTO")
            self.nextToken()
            self.labelsGotoed.add(self.curToken.text)
            self.emitter.emitLine("goto " + self.curToken.text + ';')
            self.match(TokenType.IDENT)
        # "LET" ident "=" expression
        elif self.checkToken(TokenType.let):
            print("STATEMENT-LET")
            self.nextToken()

            # Check if ident in symbols, if not we add it and emit it in headerLine
            if self.curToken.text not in self.symbols:
                self.symbols.add(self.curToken.text)
                self.emitter.headerLine("float " + self.curToken.text + ';')

            self.emitter.emit(self.curToken.text + '=')
            self.match(TokenType.IDENT)
            self.match(TokenType.EQ)
            self.expression()
            self.emitter.emitLine(';')
        # "INPUT" ident
        elif self.checkToken(TokenType.input):
            print("STATEMENT-INPUT")
            self.nextToken()

            # Check if ident in symbols, if not we add it
            if self.curToken.text not in self.symbols:
                self.symbols.add(self.curToken.text)
                self.emitter.headerLine("float " + self.curToken.text + ';')

            # Emit scanf but also validate the input. If invalid, set the variable to 0 and clear the input.
            self.emitter.emitLine("if(0 == scanf(\"%" + "f\", &" + self.curToken.text + ")) {")
            self.emitter.emitLine(self.curToken.text + " = 0;")
            self.emitter.emit("scanf(\"%")
            self.emitter.emitLine("*s\");")
            self.emitter.emitLine("}")
            self.match(TokenType.IDENT)
        # "IDENT"
        elif self.checkToken(TokenType.IDENT):
            # "IDENT" = expression
            if self.peekToken.kind is TokenType.EQ:
                print("ASSIGN-STATEMENT")
                self.emitter.emit(f"{self.curToken.text}=")
                self.nextToken()
                self.nextToken()
                self.expression()
            else:
                self.expression()
            self.emitter.emitLine(";")
        else:
            self.abort(f"Invalid statement at {self.curToken.text} ({self.curToken.kind.name})")

        self.nl() # newline

    # comparison ::= expression (("==" | "!=" | ">" | ">=" | "<" | "<=") expression)+
    def comparison(self):
        print("COMPARISON")

        self.expression()
        # Must be at least one comparison operator and another expr
        if self.isComparisonOp():
            self.emitter.emit(self.curToken.text)
            self.nextToken()
            self.expression()
        else:
            self.abort(f"Expected comparison operator at: {self.curToken.text} got ({self.curToken.kind.name})")

        while self.isComparisonOp():
            self.emitter.emit(self.curToken.text)
            self.nextToken()
            self.expression()

    # expression ::= term {( "-" | "+" ) term}
    #               | "not" expression
    #               | expression
    def expression(self):
        print("EXPRESSION")

        if self.checkToken(TokenType.not_):
            self.emitter.emit('!')
            self.nextToken()

        # 0 or 1 parenthese
        hasParent = False
        if self.checkToken(TokenType.LPARENT):
            hasParent = True
            self.emitter.emit('(')
            self.nextToken()
        self.term()
        # And then 0 or more +/- and term
        while self.checkToken(TokenType.PLUS) or self.checkToken(TokenType.MINUS):
            self.emitter.emit(self.curToken.text)
            self.nextToken()
            self.term()

        # "and" expression
        if self.checkToken(TokenType.and_):
            self.emitter.emit('&&') 
            self.nextToken()
            self.expression()
        if hasParent:
            self.match(TokenType.RPARENT)
            self.emitter.emit(')')
            self.nextToken()

    # term ::= unary {( "/" | "*" ) unary}
    def term(self):
        print("TERM")

        self.unary()
        while self.checkToken(TokenType.SLASH) or self.checkToken(TokenType.ASTERISK):
            self.emitter.emit(self.curToken.text)
            self.nextToken()
            self.unary()

    # unary ::= ["+" | "-"] primary
    def unary(self):
        print("UNARY")

        if self.checkToken(TokenType.PLUS) or self.checkToken(TokenType.MINUS):
            self.emitter.emit(self.curToken.text)
            self.nextToken()
        self.value()

    # primary ::= number | string | ident
    def value(self):
        print(f"PRIMARY ({self.curToken.text})")

        if self.checkToken(TokenType.NUMBER):
            self.emitter.emit(self.curToken.text)
            self.nextToken()
        elif self.checkToken(TokenType.STRING):
            self.emitter.emit(f'"{self.curToken.text}"')
            self.nextToken()
        elif self.checkToken(TokenType.IDENT):
            # Ensure var exists
            if self.curToken.text not in self.symbols:
                self.abort(f"Referencing variable before assignment: {self.curToken.text}")
            self.emitter.emit(self.curToken.text)
            self.nextToken()
        else:
            self.abort(f"Unexpected token at {self.curToken.text}")

    def nl(self):
        print("NEWLINE")

        # Need at least one newline
        self.match(TokenType.NEWLINE)
        # But more is fine too
        while self.checkToken(TokenType.NEWLINE):
            self.nextToken()





