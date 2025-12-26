# Copyright (c) 2025 Sean Collins, 2 Paws Machine and Engineering. All rights reserved.
#
# Licensed under the Sean Collins Software License (SCSL). See the LICENSE file in the root directory of this project
# for the full terms and conditions, including restrictions on forking, corporate use, and permissions for private/teaching purposes.

# token_type.py - Main TokenType enum combining all token types
from enum import Enum, auto

class TokenType(Enum):
    # Control Flow Keywords
    RUNTASK = auto()
    PRINTMESSAGE = auto()
    RETURNVALUE = auto()
    IFCONDITION = auto()
    THENBLOCK = auto()
    ELSEBLOCK = auto()
    TRUEBLOCK = auto()   
    FALSEBLOCK = auto()   
    WHILELOOP = auto()
    UNTILCONDITION = auto()
    FOREVERY = auto()
    IN = auto()
    TRYBLOCK = auto()
    CATCHERROR = auto()
    FINALLYBLOCK = auto()
    SENDMESSAGE = auto()
    RECEIVEMESSAGE = auto()
    EVERYINTERVAL = auto()
    BREAKLOOP = auto()
    HALTPROGRAM = auto()

    # Debug Operations
    DEBUG = auto()
    DEBUGASSERT = auto()
    DEBUGTRACE = auto()
    DEBUGBREAK = auto()
    DEBUGMEMORY = auto()
    DEBUGPERF = auto()
    DEBUGINSPECT = auto()
    DEBUGCONTROL = auto()
    CONTINUELOOP = auto()


    # Branching logic
    FORK = auto()
    BRANCH = auto()
    CASE = auto()
    DEFAULT = auto()
    TRUEPATH = auto()
    FALSEPATH = auto()


    # Pool Types
    FIXEDPOOL = auto()
    DYNAMICPOOL = auto()
    TEMPORALPOOL = auto()
    NEURALPOOL = auto()
    KERNELPOOL = auto()
    ACTORPOOL = auto()
    SECURITYPOOL = auto()
    CONSTRAINEDPOOL = auto()
    FILEPOOL = auto()
    
    # LinkagePool additions
    LINKAGEPOOL = auto()
    DIRECTION = auto()
    INOUT = auto()

    # Pool Operations
    SUBPOOL = auto()
    INITIALIZE = auto()
    CANCHANGE = auto()
    CANBENULL = auto()
    RANGE = auto()
    MAXIMUMLENGTH = auto()
    MINIMUMLENGTH = auto()
    ELEMENTTYPE = auto()
    WHERE = auto()

    #Pool management
    POOLRESIZE = auto()
    POOLMOVE = auto()
    POOLCOMPACT = auto()
    POOLALLOCATE = auto()
    HASHCREATE = auto()
    HASHFUNCTION = auto()
    HASHSET = auto()
    HASHGET = auto()
    SOCKETCREATE = auto()
    SOCKETBIND = auto()
    SOCKETLISTEN = auto()
    SOCKETACCEPT = auto()
    SOCKETREAD = auto()
    SOCKETWRITE = auto()
    SOCKETCLOSE = auto()
    SOCKETCONNECT = auto()
    SOCKETSETOPTION = auto()
    POOLFREE = auto()

    # Math Operators (Named)
    ADD = auto()
    SUBTRACT = auto()
    MULTIPLY = auto()
    DIVIDE = auto()
    POWER = auto()
    MODULO = auto()
    SQUAREROOT = auto()
    ABSOLUTEVALUE = auto()
    
    # === NEW MATH PRIMITIVES ===
    ISQRT = auto()          # Integer square root
    ABS = auto()            # Absolute value (short form)
    MIN = auto()            # Minimum of two values
    MAX = auto()            # Maximum of two values
    POW = auto()            # Power (short form)


    # Add these NEW tokens to TokenType enum (avoiding duplicates):

    # Symbol punctuation (not operators until parser decides)
    PLUS_SIGN = auto()         # + symbol
    STAR_SIGN = auto()         # * symbol  
    SLASH_SIGN = auto()        # / symbol
    PERCENT_SIGN = auto()      # % symbol (PERCENT already exists for units)
    CARET_SIGN = auto()        # ^ symbol
    GREATER_SIGN = auto()      # > symbol (GREATERTHAN already exists)
    LESS_SIGN = auto()         # < symbol (LESSTHAN already exists)
    BANG_SIGN = auto()         # ! symbol (NOT already exists)
    AMPERSAND_SIGN = auto()    # & symbol (AND already exists)
    PIPE_SIGN = auto()         # | symbol (OR already exists) 
    TILDE_SIGN = auto()        # ~ symbol

    # Two-character symbols
    EQUAL_EQUAL = auto()       # ==
    BANG_EQUAL = auto()        # !=
    GREATER_EQUAL_SIGN = auto() # >= (GREATEREQUAL already exists)
    LESS_EQUAL_SIGN = auto()   # <= (LESSEQUAL already exists)
    AND_AND = auto()           # &&
    PIPE_PIPE = auto()         # ||
    LESS_LESS = auto()         # 
    GREATER_GREATER = auto()   # >>

    # Comparison Operators (Named)
    GREATERTHAN = auto()
    LESSTHAN = auto()
    GREATEREQUAL = auto()
    LESSEQUAL = auto()
    EQUALTO = auto()
    NOTEQUAL = auto()

    # Logical Operators (Named)
    AND = auto()
    OR = auto()
    NOT = auto()
    XOR = auto()
    IMPLIES = auto()

    # Bitwise Operators (Named)
    BITWISEAND = auto()
    BITWISEOR = auto()
    BITWISEXOR = auto()
    BITWISENOT = auto()
    LEFTSHIFT = auto()
    RIGHTSHIFT = auto()

    # Interactive Input Functions
    READINPUT = auto()
    READINPUTNUMBER = auto()
    GETUSERCHOICE = auto()
    READKEY = auto()

    # String Comparison Functions
    STRINGEQUALS = auto()
    STRINGCONTAINS = auto()
    STRINGSTARTSWITH = auto()
    STRINGENDSWITH = auto()

    # String Manipulation Functions
    STRINGCONCAT = auto()
    STRINGLENGTH = auto()
    STRINGSUBSTRING = auto()
    STRINGTOUPPER = auto()
    STRINGTOLOWER = auto()
    STRINGTRIM = auto()
    STRINGREPLACE = auto()
    STRINGTOSTRING = auto()
    NUMBERTOSTRING = auto()
    STRINGTONUMBER = auto()
    # === NEW: Add missing string utilities ===
    STRINGEXTRACT = auto()
    STRINGCHARAT = auto()
    STRINGEXTRACTUNTIL = auto()
    # From new test harness
    STRINGINDEXOF = auto()
    STRINGSPLIT = auto()

    CHARTOSTRING = auto()  
    
    # === FILE I/O OPERATIONS ===
    OPENFILE = auto()
    CLOSEFILE = auto()
    READFILE = auto()
    WRITEFILE = auto()
    CREATEFILE = auto()
    DELETEFILE = auto()
    READLINE = auto()
    WRITELINE = auto()
    READTEXTFILE = auto()
    WRITETEXTFILE = auto()
    APPENDTEXTFILE = auto()
    READBINARYFILE = auto()
    WRITEBINARYFILE = auto()
    APPENDBINARYFILE = auto()
    FILEEXISTS = auto()
    GETFILESIZE = auto()
    GETFILEDATE = auto()
    SETFILEDATE = auto()
    GETFILEPERMISSIONS = auto()
    SETFILEPERMISSIONS = auto()
    SEEKPOSITION = auto()
    GETPOSITION = auto()
    REWIND = auto()
    COPYFILE = auto()
    MOVEFILE = auto()
    RENAMEFILE = auto()
    FLUSHFILE = auto()
    LOCKFILE = auto()
    UNLOCKFILE = auto()
    CREATEDIRECTORY = auto()
    DELETEDIRECTORY = auto()
    LISTDIRECTORY = auto()
    DIRECTORYEXISTS = auto()
    GETWORKINGDIRECTORY = auto()
    SETWORKINGDIRECTORY = auto()
    BUFFEREDREAD = auto()
    BUFFEREDWRITE = auto()
    SETBUFFERSIZE = auto()
    FLUSHBUFFERS = auto()

    # === NEW: LOW-LEVEL SYSTEMS PROGRAMMING TOKENS ===

    # Memory and Pointer Operations
    POINTER = auto()                    # Pointer type declaration
    DEREFERENCE = auto()               # Dereference pointer to get value
    ADDRESSOF = auto()                 # Get address of variable
    SIZEOF = auto()                    # Get size of type/variable
    ALLOCATE = auto()
    DEALLOCATE = auto()
    MEMORYCOPY = auto()                # Copy memory blocks
    MEMORYSET = auto()                 # Set memory to value
    MEMORYCOMPARE = auto()             # Compare memory blocks
    MEMCHR = auto()                    # Find character in memory
    MEMFIND = auto()                   # Find substring in memory

    STOREVALUE = auto()                # Store value to memory address

    # Hardware Register Access
    HARDWAREREGISTER = auto()          # Access CPU registers
    CONTROLREGISTER = auto()           # Access control registers (CR0, CR3, etc.)
    SEGMENTREGISTER = auto()           # Access segment registers (CS, DS, etc.)
    FLAGSREGISTER = auto()             # Access flags register
    MODELSPECIFICREGISTER = auto()     # Access MSRs

    # Port I/O Operations
    PORTREAD = auto()                  # Read from I/O port
    PORTWRITE = auto()                 # Write to I/O port
    PORTREADBYTE = auto()              # Read byte from port
    PORTWRITEBYTE = auto()             # Write byte to port
    PORTREADWORD = auto()              # Read word from port
    PORTWRITEWORD = auto()             # Write word to port
    PORTREADDWORD = auto()             # Read dword from port
    PORTWRITEDWORD = auto()            # Write dword to port

    # Interrupt and Exception Handling
    INTERRUPTHANDLER = auto()          # Define interrupt handler
    EXCEPTIONHANDLER = auto()          # Define exception handler
    ENABLEINTERRUPTS = auto()          # Enable interrupts (STI)
    DISABLEINTERRUPTS = auto()         # Disable interrupts (CLI)
    HALT = auto()                      # Halt processor (HLT)
    WAIT = auto()                      # Wait for interrupt
    TRIGGERSOFTWAREINTERRUPT = auto()  # Software interrupt (INT)
    INTERRUPTVECTOR = auto()           # Interrupt vector table

    # Atomic Operations
    ATOMICREAD = auto()                # Atomic read operation
    ATOMICWRITE = auto()               # Atomic write operation
    ATOMICADD = auto()                 # Atomic add operation
    ATOMICSUBTRACT = auto()            # Atomic subtract operation
    ATOMICCOMPARESWAP = auto()         # Compare and swap
    ATOMICEXCHANGE = auto()            # Atomic exchange
    COMPILERFENCE = auto()             # Compiler fence

    # Cache and Memory Management
    CACHEINVALIDATE = auto()           # Invalidate cache
    CACHEFLUSH = auto()                # Flush cache
    TLBINVALIDATE = auto()             # Invalidate TLB
    TLBFLUSH = auto()                  # Flush TLB
    PHYSICALMEMORY = auto()            # Physical memory access

    # Inline Assembly
    INLINEASSEMBLY = auto()            # Inline assembly block
    ASSEMBLY = auto()                  # Assembly instruction
    VOLATILE = auto()                  # Volatile memory access
    BARRIER = auto()                   # Memory/compiler barrier

    # System Calls and Kernel Operations
    PRIVILEGELEVEL = auto()            # CPU privilege level
    TASKSWITCH = auto()                # Task/context switch
    PROCESSCONTEXT = auto()            # Process context

    # Device Driver Operations
    DEVICEDRIVER = auto()              # Device driver declaration
    DEVICEREGISTER = auto()            # Device register access
    DMAOPERATION = auto()              # DMA operations
    MMIOREAD = auto()                  # Memory-mapped I/O read
    MMIOWRITE = auto()                 # Memory-mapped I/O write
    DEVICEINTERRUPT = auto()           # Device interrupt handler

    # Boot and Initialization
    BOOTLOADER = auto()                # Bootloader code
    KERNELENTRY = auto()               # Kernel entry point
    INITIALIZATION = auto()            # System initialization
    GLOBALCONSTRUCTORS = auto()        # Global constructors
    GLOBALDESTRUCTORS = auto()         # Global destructors


    # === VIRTUAL MEMORY TOKENS ===
    PAGETABLE = auto()              # PageTable operations
    VIRTUALMEMORY = auto()          # VirtualMemory operations
    MMIO = auto()                   # Memory-mapped I/O
    CACHE = auto()                  # Cache operations
    TLB = auto()                    # Translation Lookaside Buffer
    MEMORYBARRIER = auto()          # Memory barriers/fences

    # Memory Management Flags
    READONLY = auto()               # RO protection
    READWRITE = auto()              # RW protection
    READEXECUTE = auto()            # RX protection
    READWRITEEXECUTE = auto()       # RWX protection
    USERMODE = auto()               # User mode access
    KERNELMODE = auto()             # Kernel mode access
    GLOBAL = auto()                 # Global page
    DIRTY = auto()                  # Dirty bit
    ACCESSED = auto()               # Accessed bit

    # Cache Types and Levels
    CACHED = auto()                 # Cached memory
    UNCACHED = auto()               # Uncached memory
    WRITECOMBINING = auto()         # Write combining
    WRITETHROUGH = auto()           # Write through
    WRITEBACK = auto()              # Write back
    L1CACHE = auto()                # L1 cache
    L2CACHE = auto()                # L2 cache
    L3CACHE = auto()                # L3 cache

    # Page Sizes
    PAGESIZE4KB = auto()            # 4KB pages
    PAGESIZE2MB = auto()            # 2MB pages (huge)
    PAGESIZE1GB = auto()            # 1GB pages (gigantic)

    # TLB Operations
    INVALIDATE = auto()             # Invalidate operation
    FLUSH = auto()                  # Flush operation
    FLUSHALL = auto()               # Flush all operation
    FLUSHGLOBAL = auto()            # Flush global operation




    # Lambda/Function Keywords
    FUNCTION = auto()
    LAMBDA = auto()
    APPLY = auto()
    COMBINATOR = auto()
    INPUT = auto()
    OUTPUT = auto()
    BODY = auto()
    CURRY = auto()
    UNCURRY = auto()
    COMPOSE = auto()

    # Type Keywords
    INTEGER = auto()
    FLOATINGPOINT = auto()
    TEXT = auto()
    BOOLEAN = auto()
    ADDRESS = auto()
    ARRAY = auto()
    MAP = auto()
    TUPLE = auto()
    RECORD = auto()
    OPTIONALTYPE = auto()
    CONSTRAINEDTYPE = auto()
    ANY = auto()
    VOID = auto()

    # === NEW: Low-Level Type Keywords ===
    BYTE = auto()                      # 8-bit unsigned integer
    WORD = auto()                      # 16-bit unsigned integer
    DWORD = auto()                     # 32-bit unsigned integer
    QWORD = auto()                     # 64-bit unsigned integer
    UINT8 = auto()                     # 8-bit unsigned
    UINT16 = auto()                    # 16-bit unsigned
    UINT32 = auto()                    # 32-bit unsigned
    UINT64 = auto()                    # 64-bit unsigned
    INT8 = auto()                      # 8-bit signed
    INT16 = auto()                     # 16-bit signed
    INT32 = auto()                     # 32-bit signed
    INT64 = auto()                     # 64-bit signed





    # Macro Keywords
    MACROBLOCK = auto()
    MACRO = auto()
    RUNMACRO = auto()
    EXPANDMACRO = auto()

    # Security Keywords
    SECURITYCONTEXT = auto()
    WITHSECURITY = auto()
    ALLOWEDOPERATIONS = auto()
    DENIEDOPERATIONS = auto()
    MEMORYLIMIT = auto()
    CPUQUOTA = auto()
    LEVEL = auto()

    # System/Hardware Keywords
    HARDWARE = auto()
    SYSCALL = auto()
    INTERRUPT = auto()
    REGISTER = auto()
    MEMORY = auto()
    PHYSICALADDRESS = auto()
    VIRTUALADDRESS = auto()
    FLAGS = auto()

    # Code Organization
    SUBROUTINE = auto()
    LIBRARYIMPORT = auto()
    LOOPMAIN = auto()
    LOOPACTOR = auto()
    LOOPSTART = auto()
    LOOPEND = auto()
    LOOPSHADOW = auto()

    # Constants/Values
    TRUE = auto()
    FALSE = auto()
    NULL = auto()
    AUTOMATIC = auto()
    UNLIMITED = auto()

    # Mathematical Constants
    CONSTANT = auto()
    PI = auto()
    E = auto()
    PHI = auto()

    # Units
    BYTES = auto()
    KILOBYTES = auto()
    MEGABYTES = auto()
    GIGABYTES = auto()
    SECONDS = auto()
    MILLISECONDS = auto()
    MICROSECONDS = auto()
    PERCENT = auto()

    # Delimiters
    DOT = auto()
    LBRACE = auto()
    RBRACE = auto()
    LPAREN = auto()
    RPAREN = auto()
    LBRACKET = auto()
    RBRACKET = auto()
    COMMA = auto()
    COLON = auto()
    SEMICOLON = auto()
    DASH = auto()
    EQUALS = auto()
    ARROW = auto()

    # Literals
    IDENTIFIER = auto()
    NUMBER = auto()
    STRING = auto()

    # Comments
    COMMENT = auto()
    DOC_COMMENT = auto()
    COM_COMMENT = auto()
    TAG_COMMENT = auto()

    # Special
    EOF = auto()
    NEWLINE = auto()

    # Error token
    ERROR = auto()