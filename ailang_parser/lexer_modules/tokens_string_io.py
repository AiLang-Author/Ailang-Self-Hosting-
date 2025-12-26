# Copyright (c) 2025 Sean Collins, 2 Paws Machine and Engineering. All rights reserved.
#
# Licensed under the Sean Collins Software License (SCSL). See the LICENSE file in the root directory of this project
# for the full terms and conditions, including restrictions on forking, corporate use, and permissions for private/teaching purposes.

# tokens_string_io.py - String and I/O Operation Token Types
from enum import Enum, auto

class StringTokens(Enum):
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
    CHARTOSTRING = auto()

class FileIOTokens(Enum):
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