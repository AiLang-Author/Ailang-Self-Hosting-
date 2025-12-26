#!/usr/bin/env python3

# Copyright (c) 2025 Sean Collins, 2 Paws Machine and Engineering. All rights reserved.
#
# Licensed under the Sean Collins Software License (SCSL). See the LICENSE file in the root directory of this project
# for the full terms and conditions, including restrictions on forking, corporate use, and permissions for private/teaching purposes.
#!/usr/bin/env python3
"""
Linux x86-64 System Call Table
Comprehensive reference implementation for all Linux syscalls
Designed to be swappable for other operating systems (BSD, Windows, etc.)
"""

from dataclasses import dataclass
from typing import List, Optional, Dict
from enum import IntEnum

class SyscallCategory(IntEnum):
    """Categories for organizing syscalls"""
    PROCESS = 1
    FILE_IO = 2
    MEMORY = 3
    NETWORK = 4
    IPC = 5
    TIME = 6
    SIGNAL = 7
    SYSTEM = 8
    SECURITY = 9

@dataclass
class SyscallDescriptor:
    """Describes a single system call"""
    number: int
    name: str
    num_args: int
    category: SyscallCategory
    description: str
    arg_names: List[str]
    return_type: str = "int"
    
    def __repr__(self):
        args = ", ".join(self.arg_names)
        return f"{self.name}({args}) -> {self.return_type}  [syscall {self.number}]"


class LinuxX86_64SyscallTable:
    """Complete Linux x86-64 syscall table (kernel 6.x)"""
    
    def __init__(self):
        self.syscalls: Dict[int, SyscallDescriptor] = {}
        self.syscalls_by_name: Dict[str, SyscallDescriptor] = {}
        self._initialize_table()
    
    def _initialize_table(self):
        """Initialize the complete syscall table"""
        
        # === PROCESS MANAGEMENT ===
        self._add(0, "read", 3, SyscallCategory.FILE_IO,
                  "Read from file descriptor",
                  ["fd", "buf", "count"])
        
        self._add(1, "write", 3, SyscallCategory.FILE_IO,
                  "Write to file descriptor",
                  ["fd", "buf", "count"])
        
        self._add(2, "open", 3, SyscallCategory.FILE_IO,
                  "Open file",
                  ["filename", "flags", "mode"])
        
        self._add(3, "close", 1, SyscallCategory.FILE_IO,
                  "Close file descriptor",
                  ["fd"])
        
        self._add(4, "stat", 2, SyscallCategory.FILE_IO,
                  "Get file status",
                  ["filename", "statbuf"])
        
        self._add(5, "fstat", 2, SyscallCategory.FILE_IO,
                  "Get file status by fd",
                  ["fd", "statbuf"])
        
        self._add(6, "lstat", 2, SyscallCategory.FILE_IO,
                  "Get file status (don't follow symlinks)",
                  ["filename", "statbuf"])
        
        self._add(7, "poll", 3, SyscallCategory.FILE_IO,
                  "Wait for events on file descriptors",
                  ["fds", "nfds", "timeout"])
        
        self._add(8, "lseek", 3, SyscallCategory.FILE_IO,
                  "Reposition file offset",
                  ["fd", "offset", "whence"])
        
        self._add(9, "mmap", 6, SyscallCategory.MEMORY,
                  "Map files or devices into memory",
                  ["addr", "length", "prot", "flags", "fd", "offset"])
        
        self._add(10, "mprotect", 3, SyscallCategory.MEMORY,
                  "Set protection on memory region",
                  ["addr", "len", "prot"])
        
        self._add(11, "munmap", 2, SyscallCategory.MEMORY,
                  "Unmap memory region",
                  ["addr", "length"])
        
        self._add(12, "brk", 1, SyscallCategory.MEMORY,
                  "Change data segment size",
                  ["addr"])
        
        self._add(13, "rt_sigaction", 4, SyscallCategory.SIGNAL,
                  "Examine/change signal action",
                  ["signum", "act", "oldact", "sigsetsize"])
        
        self._add(14, "rt_sigprocmask", 4, SyscallCategory.SIGNAL,
                  "Examine/change blocked signals",
                  ["how", "set", "oldset", "sigsetsize"])
        
        self._add(15, "rt_sigreturn", 0, SyscallCategory.SIGNAL,
                  "Return from signal handler",
                  [])
        
        self._add(16, "ioctl", 3, SyscallCategory.FILE_IO,
                  "Control device",
                  ["fd", "request", "argp"])
        
        self._add(17, "pread64", 4, SyscallCategory.FILE_IO,
                  "Read from fd at offset",
                  ["fd", "buf", "count", "offset"])
        
        self._add(18, "pwrite64", 4, SyscallCategory.FILE_IO,
                  "Write to fd at offset",
                  ["fd", "buf", "count", "offset"])
        
        self._add(19, "readv", 3, SyscallCategory.FILE_IO,
                  "Read into multiple buffers",
                  ["fd", "iov", "iovcnt"])
        
        self._add(20, "writev", 3, SyscallCategory.FILE_IO,
                  "Write from multiple buffers",
                  ["fd", "iov", "iovcnt"])
        
        self._add(21, "access", 2, SyscallCategory.FILE_IO,
                  "Check user's permissions for file",
                  ["filename", "mode"])
        
        self._add(22, "pipe", 1, SyscallCategory.IPC,
                  "Create pipe",
                  ["pipefd"])
        
        self._add(23, "select", 5, SyscallCategory.FILE_IO,
                  "Synchronous I/O multiplexing",
                  ["nfds", "readfds", "writefds", "exceptfds", "timeout"])
        
        self._add(24, "sched_yield", 0, SyscallCategory.PROCESS,
                  "Yield the processor",
                  [])
        
        self._add(25, "mremap", 5, SyscallCategory.MEMORY,
                  "Remap virtual memory address",
                  ["old_address", "old_size", "new_size", "flags", "new_address"])
        
        self._add(26, "msync", 3, SyscallCategory.MEMORY,
                  "Synchronize memory with physical storage",
                  ["addr", "length", "flags"])
        
        self._add(27, "mincore", 3, SyscallCategory.MEMORY,
                  "Determine memory residency",
                  ["addr", "length", "vec"])
        
        self._add(28, "madvise", 3, SyscallCategory.MEMORY,
                  "Give advice about memory usage",
                  ["addr", "length", "advice"])
        
        self._add(29, "shmget", 3, SyscallCategory.IPC,
                  "Allocate shared memory segment",
                  ["key", "size", "shmflg"])
        
        self._add(30, "shmat", 3, SyscallCategory.IPC,
                  "Attach shared memory segment",
                  ["shmid", "shmaddr", "shmflg"])
        
        self._add(31, "shmctl", 3, SyscallCategory.IPC,
                  "Shared memory control",
                  ["shmid", "cmd", "buf"])
        
        self._add(32, "dup", 1, SyscallCategory.FILE_IO,
                  "Duplicate file descriptor",
                  ["oldfd"])
        
        self._add(33, "dup2", 2, SyscallCategory.FILE_IO,
                  "Duplicate file descriptor to specific fd",
                  ["oldfd", "newfd"])
        
        self._add(34, "pause", 0, SyscallCategory.SIGNAL,
                  "Wait for signal",
                  [])
        
        self._add(35, "nanosleep", 2, SyscallCategory.TIME,
                  "High-resolution sleep",
                  ["req", "rem"])
        
        self._add(36, "getitimer", 2, SyscallCategory.TIME,
                  "Get value of interval timer",
                  ["which", "curr_value"])
        
        self._add(37, "alarm", 1, SyscallCategory.TIME,
                  "Set alarm clock",
                  ["seconds"])
        
        self._add(38, "setitimer", 3, SyscallCategory.TIME,
                  "Set value of interval timer",
                  ["which", "new_value", "old_value"])
        
        self._add(39, "getpid", 0, SyscallCategory.PROCESS,
                  "Get process ID",
                  [])
        
        self._add(40, "sendfile", 4, SyscallCategory.FILE_IO,
                  "Transfer data between file descriptors",
                  ["out_fd", "in_fd", "offset", "count"])
        
        self._add(41, "socket", 3, SyscallCategory.NETWORK,
                  "Create endpoint for communication",
                  ["domain", "type", "protocol"])
        
        self._add(42, "connect", 3, SyscallCategory.NETWORK,
                  "Initiate connection on socket",
                  ["sockfd", "addr", "addrlen"])
        
        self._add(43, "accept", 3, SyscallCategory.NETWORK,
                  "Accept connection on socket",
                  ["sockfd", "addr", "addrlen"])
        
        self._add(44, "sendto", 6, SyscallCategory.NETWORK,
                  "Send message on socket",
                  ["sockfd", "buf", "len", "flags", "dest_addr", "addrlen"])
        
        self._add(45, "recvfrom", 6, SyscallCategory.NETWORK,
                  "Receive message from socket",
                  ["sockfd", "buf", "len", "flags", "src_addr", "addrlen"])
        
        self._add(46, "sendmsg", 3, SyscallCategory.NETWORK,
                  "Send message on socket",
                  ["sockfd", "msg", "flags"])
        
        self._add(47, "recvmsg", 3, SyscallCategory.NETWORK,
                  "Receive message from socket",
                  ["sockfd", "msg", "flags"])
        
        self._add(48, "shutdown", 2, SyscallCategory.NETWORK,
                  "Shut down part of full-duplex connection",
                  ["sockfd", "how"])
        
        self._add(49, "bind", 3, SyscallCategory.NETWORK,
                  "Bind name to socket",
                  ["sockfd", "addr", "addrlen"])
        
        self._add(50, "listen", 2, SyscallCategory.NETWORK,
                  "Listen for connections on socket",
                  ["sockfd", "backlog"])
        
        self._add(51, "getsockname", 3, SyscallCategory.NETWORK,
                  "Get socket name",
                  ["sockfd", "addr", "addrlen"])
        
        self._add(52, "getpeername", 3, SyscallCategory.NETWORK,
                  "Get name of connected peer",
                  ["sockfd", "addr", "addrlen"])
        
        self._add(53, "socketpair", 4, SyscallCategory.NETWORK,
                  "Create pair of connected sockets",
                  ["domain", "type", "protocol", "sv"])
        
        self._add(54, "setsockopt", 5, SyscallCategory.NETWORK,
                  "Set socket options",
                  ["sockfd", "level", "optname", "optval", "optlen"])
        
        self._add(55, "getsockopt", 5, SyscallCategory.NETWORK,
                  "Get socket options",
                  ["sockfd", "level", "optname", "optval", "optlen"])
        
        self._add(56, "clone", 5, SyscallCategory.PROCESS,
                  "Create child process or thread",
                  ["flags", "stack", "parent_tid", "child_tid", "tls"])
        
        self._add(57, "fork", 0, SyscallCategory.PROCESS,
                  "Create child process",
                  [])
        
        self._add(58, "vfork", 0, SyscallCategory.PROCESS,
                  "Create child process (shares memory)",
                  [])
        
        self._add(59, "execve", 3, SyscallCategory.PROCESS,
                  "Execute program",
                  ["filename", "argv", "envp"])
        
        self._add(60, "exit", 1, SyscallCategory.PROCESS,
                  "Terminate calling process",
                  ["status"])
        
        self._add(61, "wait4", 4, SyscallCategory.PROCESS,
                  "Wait for process to change state",
                  ["pid", "status", "options", "rusage"])
        
        self._add(62, "kill", 2, SyscallCategory.SIGNAL,
                  "Send signal to process",
                  ["pid", "sig"])
        
        self._add(63, "uname", 1, SyscallCategory.SYSTEM,
                  "Get system information",
                  ["buf"])
        
        self._add(64, "semget", 3, SyscallCategory.IPC,
                  "Get semaphore set",
                  ["key", "nsems", "semflg"])
        
        self._add(65, "semop", 3, SyscallCategory.IPC,
                  "Semaphore operations",
                  ["semid", "sops", "nsops"])
        
        self._add(66, "semctl", 4, SyscallCategory.IPC,
                  "Semaphore control",
                  ["semid", "semnum", "cmd", "arg"])
        
        self._add(67, "shmdt", 1, SyscallCategory.IPC,
                  "Detach shared memory segment",
                  ["shmaddr"])
        
        self._add(68, "msgget", 2, SyscallCategory.IPC,
                  "Get message queue",
                  ["key", "msgflg"])
        
        self._add(69, "msgsnd", 4, SyscallCategory.IPC,
                  "Send message",
                  ["msqid", "msgp", "msgsz", "msgflg"])
        
        self._add(70, "msgrcv", 5, SyscallCategory.IPC,
                  "Receive message",
                  ["msqid", "msgp", "msgsz", "msgtyp", "msgflg"])
        
        self._add(71, "msgctl", 3, SyscallCategory.IPC,
                  "Message control",
                  ["msqid", "cmd", "buf"])
        
        self._add(72, "fcntl", 3, SyscallCategory.FILE_IO,
                  "Manipulate file descriptor",
                  ["fd", "cmd", "arg"])
        
        self._add(73, "flock", 2, SyscallCategory.FILE_IO,
                  "Apply/remove advisory lock on file",
                  ["fd", "operation"])
        
        self._add(74, "fsync", 1, SyscallCategory.FILE_IO,
                  "Synchronize file's in-core state",
                  ["fd"])
        
        self._add(75, "fdatasync", 1, SyscallCategory.FILE_IO,
                  "Synchronize file's data",
                  ["fd"])
        
        self._add(76, "truncate", 2, SyscallCategory.FILE_IO,
                  "Truncate file to specified length",
                  ["path", "length"])
        
        self._add(77, "ftruncate", 2, SyscallCategory.FILE_IO,
                  "Truncate file to specified length",
                  ["fd", "length"])
        
        self._add(78, "getdents", 3, SyscallCategory.FILE_IO,
                  "Get directory entries",
                  ["fd", "dirp", "count"])
        
        self._add(79, "getcwd", 2, SyscallCategory.FILE_IO,
                  "Get current working directory",
                  ["buf", "size"])
        
        self._add(80, "chdir", 1, SyscallCategory.FILE_IO,
                  "Change working directory",
                  ["path"])
        
        self._add(81, "fchdir", 1, SyscallCategory.FILE_IO,
                  "Change working directory",
                  ["fd"])
        
        self._add(82, "rename", 2, SyscallCategory.FILE_IO,
                  "Rename file",
                  ["oldpath", "newpath"])
        
        self._add(83, "mkdir", 2, SyscallCategory.FILE_IO,
                  "Create directory",
                  ["pathname", "mode"])
        
        self._add(84, "rmdir", 1, SyscallCategory.FILE_IO,
                  "Remove directory",
                  ["pathname"])
        
        self._add(85, "creat", 2, SyscallCategory.FILE_IO,
                  "Create file",
                  ["pathname", "mode"])
        
        self._add(86, "link", 2, SyscallCategory.FILE_IO,
                  "Create hard link",
                  ["oldpath", "newpath"])
        
        self._add(87, "unlink", 1, SyscallCategory.FILE_IO,
                  "Delete file",
                  ["pathname"])
        
        self._add(88, "symlink", 2, SyscallCategory.FILE_IO,
                  "Create symbolic link",
                  ["target", "linkpath"])
        
        self._add(89, "readlink", 3, SyscallCategory.FILE_IO,
                  "Read symbolic link",
                  ["pathname", "buf", "bufsiz"])
        
        self._add(90, "chmod", 2, SyscallCategory.FILE_IO,
                  "Change file permissions",
                  ["pathname", "mode"])
        
        self._add(91, "fchmod", 2, SyscallCategory.FILE_IO,
                  "Change file permissions",
                  ["fd", "mode"])
        
        self._add(92, "chown", 3, SyscallCategory.FILE_IO,
                  "Change file owner",
                  ["pathname", "owner", "group"])
        
        self._add(93, "fchown", 3, SyscallCategory.FILE_IO,
                  "Change file owner",
                  ["fd", "owner", "group"])
        
        self._add(94, "lchown", 3, SyscallCategory.FILE_IO,
                  "Change file owner (don't follow symlinks)",
                  ["pathname", "owner", "group"])
        
        self._add(95, "umask", 1, SyscallCategory.FILE_IO,
                  "Set file mode creation mask",
                  ["mask"])
        
        self._add(96, "gettimeofday", 2, SyscallCategory.TIME,
                  "Get time",
                  ["tv", "tz"])
        
        self._add(97, "getrlimit", 2, SyscallCategory.SYSTEM,
                  "Get resource limits",
                  ["resource", "rlim"])
        
        self._add(98, "getrusage", 2, SyscallCategory.SYSTEM,
                  "Get resource usage",
                  ["who", "usage"])
        
        self._add(99, "sysinfo", 1, SyscallCategory.SYSTEM,
                  "Get system information",
                  ["info"])
        
        self._add(100, "times", 1, SyscallCategory.TIME,
                  "Get process times",
                  ["buf"])
        
        self._add(101, "ptrace", 4, SyscallCategory.PROCESS,
                  "Process trace",
                  ["request", "pid", "addr", "data"])
        
        self._add(102, "getuid", 0, SyscallCategory.SECURITY,
                  "Get user identity",
                  [])
        
        self._add(103, "syslog", 3, SyscallCategory.SYSTEM,
                  "Read/clear kernel message ring buffer",
                  ["type", "bufp", "len"])
        
        self._add(104, "getgid", 0, SyscallCategory.SECURITY,
                  "Get group identity",
                  [])
        
        self._add(105, "setuid", 1, SyscallCategory.SECURITY,
                  "Set user identity",
                  ["uid"])
        
        self._add(106, "setgid", 1, SyscallCategory.SECURITY,
                  "Set group identity",
                  ["gid"])
        
        self._add(107, "geteuid", 0, SyscallCategory.SECURITY,
                  "Get effective user ID",
                  [])
        
        self._add(108, "getegid", 0, SyscallCategory.SECURITY,
                  "Get effective group ID",
                  [])
        
        self._add(109, "setpgid", 2, SyscallCategory.PROCESS,
                  "Set process group ID",
                  ["pid", "pgid"])
        
        self._add(110, "getppid", 0, SyscallCategory.PROCESS,
                  "Get parent process ID",
                  [])
        
        self._add(111, "getpgrp", 0, SyscallCategory.PROCESS,
                  "Get process group",
                  [])
        
        self._add(112, "setsid", 0, SyscallCategory.PROCESS,
                  "Create session and set process group ID",
                  [])
        
        self._add(113, "setreuid", 2, SyscallCategory.SECURITY,
                  "Set real and effective user IDs",
                  ["ruid", "euid"])
        
        self._add(114, "setregid", 2, SyscallCategory.SECURITY,
                  "Set real and effective group IDs",
                  ["rgid", "egid"])
        
        self._add(115, "getgroups", 2, SyscallCategory.SECURITY,
                  "Get supplementary group IDs",
                  ["size", "list"])
        
        self._add(116, "setgroups", 2, SyscallCategory.SECURITY,
                  "Set supplementary group IDs",
                  ["size", "list"])
        
        self._add(117, "setresuid", 3, SyscallCategory.SECURITY,
                  "Set real, effective, saved user IDs",
                  ["ruid", "euid", "suid"])
        
        self._add(118, "getresuid", 3, SyscallCategory.SECURITY,
                  "Get real, effective, saved user IDs",
                  ["ruid", "euid", "suid"])
        
        self._add(119, "setresgid", 3, SyscallCategory.SECURITY,
                  "Set real, effective, saved group IDs",
                  ["rgid", "egid", "sgid"])
        
        self._add(120, "getresgid", 3, SyscallCategory.SECURITY,
                  "Get real, effective, saved group IDs",
                  ["rgid", "egid", "sgid"])
        
        self._add(121, "getpgid", 1, SyscallCategory.PROCESS,
                  "Get process group ID",
                  ["pid"])
        
        self._add(122, "setfsuid", 1, SyscallCategory.SECURITY,
                  "Set filesystem user ID",
                  ["uid"])
        
        self._add(123, "setfsgid", 1, SyscallCategory.SECURITY,
                  "Set filesystem group ID",
                  ["gid"])
        
        self._add(124, "getsid", 1, SyscallCategory.PROCESS,
                  "Get session ID",
                  ["pid"])
        
        self._add(125, "capget", 2, SyscallCategory.SECURITY,
                  "Get capabilities",
                  ["hdrp", "datap"])
        
        self._add(126, "capset", 2, SyscallCategory.SECURITY,
                  "Set capabilities",
                  ["hdrp", "datap"])
        
        self._add(127, "rt_sigpending", 2, SyscallCategory.SIGNAL,
                  "Examine pending signals",
                  ["set", "sigsetsize"])
        
        self._add(128, "rt_sigtimedwait", 4, SyscallCategory.SIGNAL,
                  "Synchronously wait for queued signals",
                  ["uthese", "uinfo", "uts", "sigsetsize"])
        
        self._add(129, "rt_sigqueueinfo", 3, SyscallCategory.SIGNAL,
                  "Queue signal and data",
                  ["pid", "sig", "uinfo"])
        
        self._add(130, "rt_sigsuspend", 2, SyscallCategory.SIGNAL,
                  "Wait for signal",
                  ["unewset", "sigsetsize"])
        
        self._add(131, "sigaltstack", 2, SyscallCategory.SIGNAL,
                  "Set/get signal stack context",
                  ["uss", "uoss"])
        
        self._add(132, "utime", 2, SyscallCategory.FILE_IO,
                  "Change file last access/modification times",
                  ["filename", "times"])
        
        self._add(133, "mknod", 3, SyscallCategory.FILE_IO,
                  "Create special or ordinary file",
                  ["filename", "mode", "dev"])
        
        self._add(134, "uselib", 1, SyscallCategory.SYSTEM,
                  "Load shared library (obsolete)",
                  ["library"])
        
        self._add(135, "personality", 1, SyscallCategory.SYSTEM,
                  "Set process execution domain",
                  ["personality"])
        
        self._add(136, "ustat", 2, SyscallCategory.FILE_IO,
                  "Get filesystem statistics (obsolete)",
                  ["dev", "ubuf"])
        
        self._add(137, "statfs", 2, SyscallCategory.FILE_IO,
                  "Get filesystem statistics",
                  ["path", "buf"])
        
        self._add(138, "fstatfs", 2, SyscallCategory.FILE_IO,
                  "Get filesystem statistics",
                  ["fd", "buf"])
        
        self._add(139, "sysfs", 3, SyscallCategory.SYSTEM,
                  "Get filesystem type information",
                  ["option", "arg1", "arg2"])
        
        self._add(140, "getpriority", 2, SyscallCategory.PROCESS,
                  "Get program scheduling priority",
                  ["which", "who"])
        
        self._add(141, "setpriority", 3, SyscallCategory.PROCESS,
                  "Set program scheduling priority",
                  ["which", "who", "niceval"])
        
        self._add(142, "sched_setparam", 2, SyscallCategory.PROCESS,
                  "Set scheduling parameters",
                  ["pid", "param"])
        
        self._add(143, "sched_getparam", 2, SyscallCategory.PROCESS,
                  "Get scheduling parameters",
                  ["pid", "param"])
        
        self._add(144, "sched_setscheduler", 3, SyscallCategory.PROCESS,
                  "Set scheduling algorithm/parameters",
                  ["pid", "policy", "param"])
        
        self._add(145, "sched_getscheduler", 1, SyscallCategory.PROCESS,
                  "Get scheduling algorithm",
                  ["pid"])
        
        self._add(146, "sched_get_priority_max", 1, SyscallCategory.PROCESS,
                  "Get max static priority",
                  ["policy"])
        
        self._add(147, "sched_get_priority_min", 1, SyscallCategory.PROCESS,
                  "Get min static priority",
                  ["policy"])
        
        self._add(148, "sched_rr_get_interval", 2, SyscallCategory.PROCESS,
                  "Get SCHED_RR interval",
                  ["pid", "interval"])
        
        self._add(149, "mlock", 2, SyscallCategory.MEMORY,
                  "Lock memory pages",
                  ["start", "len"])
        
        self._add(150, "munlock", 2, SyscallCategory.MEMORY,
                  "Unlock memory pages",
                  ["start", "len"])
        
        self._add(151, "mlockall", 1, SyscallCategory.MEMORY,
                  "Lock all memory pages",
                  ["flags"])
        
        self._add(152, "munlockall", 0, SyscallCategory.MEMORY,
                  "Unlock all memory pages",
                  [])
        
        self._add(153, "vhangup", 0, SyscallCategory.SYSTEM,
                  "Virtually hangup current terminal",
                  [])
        
        self._add(154, "modify_ldt", 3, SyscallCategory.SYSTEM,
                  "Read/write local descriptor table",
                  ["func", "ptr", "bytecount"])
        
        self._add(155, "pivot_root", 2, SyscallCategory.FILE_IO,
                  "Change root filesystem",
                  ["new_root", "put_old"])
        
        self._add(156, "_sysctl", 1, SyscallCategory.SYSTEM,
                  "Read/write system parameters (obsolete)",
                  ["args"])
        
        self._add(157, "prctl", 5, SyscallCategory.PROCESS,
                  "Operations on a process",
                  ["option", "arg2", "arg3", "arg4", "arg5"])
        
        self._add(158, "arch_prctl", 2, SyscallCategory.SYSTEM,
                  "Set architecture-specific thread state",
                  ["code", "addr"])
        
        self._add(159, "adjtimex", 1, SyscallCategory.TIME,
                  "Tune kernel clock",
                  ["txc_p"])
        
        self._add(160, "setrlimit", 2, SyscallCategory.SYSTEM,
                  "Set resource limits",
                  ["resource", "rlim"])
        
        self._add(161, "chroot", 1, SyscallCategory.FILE_IO,
                  "Change root directory",
                  ["filename"])
        
        self._add(162, "sync", 0, SyscallCategory.FILE_IO,
                  "Commit filesystem caches to disk",
                  [])
        
        self._add(163, "acct", 1, SyscallCategory.SYSTEM,
                  "Switch process accounting on/off",
                  ["name"])
        
        self._add(164, "settimeofday", 2, SyscallCategory.TIME,
                  "Set time",
                  ["tv", "tz"])
        
        self._add(165, "mount", 5, SyscallCategory.FILE_IO,
                  "Mount filesystem",
                  ["dev_name", "dir_name", "type", "flags", "data"])
        
        self._add(166, "umount2", 2, SyscallCategory.FILE_IO,
                  "Unmount filesystem",
                  ["name", "flags"])
        
        self._add(167, "swapon", 2, SyscallCategory.MEMORY,
                  "Start swapping to file/device",
                  ["specialfile", "swap_flags"])
        
        self._add(168, "swapoff", 1, SyscallCategory.MEMORY,
                  "Stop swapping to file/device",
                  ["specialfile"])
        
        self._add(169, "reboot", 4, SyscallCategory.SYSTEM,
                  "Reboot or enable/disable Ctrl-Alt-Del",
                  ["magic1", "magic2", "cmd", "arg"])
        
        self._add(170, "sethostname", 2, SyscallCategory.SYSTEM,
                  "Set hostname",
                  ["name", "len"])
        
        self._add(171, "setdomainname", 2, SyscallCategory.SYSTEM,
                  "Set NIS domain name",
                  ["name", "len"])
        
        self._add(172, "iopl", 1, SyscallCategory.SYSTEM,
                  "Change I/O privilege level",
                  ["level"])
        
        self._add(173, "ioperm", 3, SyscallCategory.SYSTEM,
                  "Set port I/O permissions",
                  ["from", "num", "on"])
        
        self._add(174, "create_module", 2, SyscallCategory.SYSTEM,
                  "Create loadable module entry (obsolete)",
                  ["name", "size"])
        
        self._add(175, "init_module", 3, SyscallCategory.SYSTEM,
                  "Load kernel module",
                  ["umod", "len", "uargs"])
        
        self._add(176, "delete_module", 2, SyscallCategory.SYSTEM,
                  "Unload kernel module",
                  ["name_user", "flags"])
        
        self._add(177, "get_kernel_syms", 1, SyscallCategory.SYSTEM,
                  "Get exported kernel symbols (obsolete)",
                  ["table"])
        
        self._add(178, "query_module", 5, SyscallCategory.SYSTEM,
                  "Query module (obsolete)",
                  ["name", "which", "buf", "bufsize", "ret"])
        
        self._add(179, "quotactl", 4, SyscallCategory.FILE_IO,
                  "Manipulate disk quotas",
                  ["cmd", "special", "id", "addr"])
        
        self._add(180, "nfsservctl", 3, SyscallCategory.FILE_IO,
                  "NFS daemon (obsolete)",
                  ["cmd", "argp", "resp"])
        
        self._add(181, "getpmsg", 5, SyscallCategory.IPC,
                  "Get message from STREAMS (unimplemented)",
                  ["fildes", "ctlptr", "dataptr", "bandp", "flagsp"])
        
        self._add(182, "putpmsg", 5, SyscallCategory.IPC,
                  "Send message on STREAMS (unimplemented)",
                  ["fildes", "ctlptr", "dataptr", "band", "flags"])
        
        self._add(183, "afs_syscall", 0, SyscallCategory.SYSTEM,
                  "AFS syscall (unimplemented)",
                  [])
        
        self._add(184, "tuxcall", 0, SyscallCategory.SYSTEM,
                  "Tux web server (unimplemented)",
                  [])
        
        self._add(185, "security", 0, SyscallCategory.SECURITY,
                  "Security module (unimplemented)",
                  [])
        
        self._add(186, "gettid", 0, SyscallCategory.PROCESS,
                  "Get thread ID",
                  [])
        
        self._add(187, "readahead", 3, SyscallCategory.FILE_IO,
                  "Initiate file readahead into page cache",
                  ["fd", "offset", "count"])
        
        self._add(188, "setxattr", 5, SyscallCategory.FILE_IO,
                  "Set extended attribute",
                  ["pathname", "name", "value", "size", "flags"])
        
        self._add(189, "lsetxattr", 5, SyscallCategory.FILE_IO,
                  "Set extended attribute (don't follow symlinks)",
                  ["pathname", "name", "value", "size", "flags"])
        
        self._add(190, "fsetxattr", 5, SyscallCategory.FILE_IO,
                  "Set extended attribute by fd",
                  ["fd", "name", "value", "size", "flags"])
        
        self._add(191, "getxattr", 4, SyscallCategory.FILE_IO,
                  "Get extended attribute",
                  ["pathname", "name", "value", "size"])
        
        self._add(192, "lgetxattr", 4, SyscallCategory.FILE_IO,
                  "Get extended attribute (don't follow symlinks)",
                  ["pathname", "name", "value", "size"])
        
        self._add(193, "fgetxattr", 4, SyscallCategory.FILE_IO,
                  "Get extended attribute by fd",
                  ["fd", "name", "value", "size"])
        
        self._add(194, "listxattr", 3, SyscallCategory.FILE_IO,
                  "List extended attributes",
                  ["pathname", "list", "size"])
        
        self._add(195, "llistxattr", 3, SyscallCategory.FILE_IO,
                  "List extended attributes (don't follow symlinks)",
                  ["pathname", "list", "size"])
        
        self._add(196, "flistxattr", 3, SyscallCategory.FILE_IO,
                  "List extended attributes by fd",
                  ["fd", "list", "size"])
        
        self._add(197, "removexattr", 2, SyscallCategory.FILE_IO,
                  "Remove extended attribute",
                  ["pathname", "name"])
        
        self._add(198, "lremovexattr", 2, SyscallCategory.FILE_IO,
                  "Remove extended attribute (don't follow symlinks)",
                  ["pathname", "name"])
        
        self._add(199, "fremovexattr", 2, SyscallCategory.FILE_IO,
                  "Remove extended attribute by fd",
                  ["fd", "name"])
        
        self._add(200, "tkill", 2, SyscallCategory.SIGNAL,
                  "Send signal to thread",
                  ["tid", "sig"])
        
        self._add(201, "time", 1, SyscallCategory.TIME,
                  "Get time in seconds",
                  ["tloc"])
        
        self._add(202, "futex", 6, SyscallCategory.IPC,
                  "Fast userspace locking",
                  ["uaddr", "op", "val", "timeout", "uaddr2", "val3"])
        
        self._add(203, "sched_setaffinity", 3, SyscallCategory.PROCESS,
                  "Set CPU affinity",
                  ["pid", "len", "user_mask_ptr"])
        
        self._add(204, "sched_getaffinity", 3, SyscallCategory.PROCESS,
                  "Get CPU affinity",
                  ["pid", "len", "user_mask_ptr"])
        
        self._add(205, "set_thread_area", 1, SyscallCategory.PROCESS,
                  "Set thread-local storage",
                  ["u_info"])
        
        self._add(206, "io_setup", 2, SyscallCategory.FILE_IO,
                  "Create asynchronous I/O context",
                  ["nr_events", "ctxp"])
        
        self._add(207, "io_destroy", 1, SyscallCategory.FILE_IO,
                  "Destroy asynchronous I/O context",
                  ["ctx"])
        
        self._add(208, "io_getevents", 5, SyscallCategory.FILE_IO,
                  "Read asynchronous I/O events",
                  ["ctx_id", "min_nr", "nr", "events", "timeout"])
        
        self._add(209, "io_submit", 3, SyscallCategory.FILE_IO,
                  "Submit asynchronous I/O blocks",
                  ["ctx_id", "nr", "iocbpp"])
        
        self._add(210, "io_cancel", 3, SyscallCategory.FILE_IO,
                  "Cancel asynchronous I/O",
                  ["ctx_id", "iocb", "result"])
        
        self._add(211, "get_thread_area", 1, SyscallCategory.PROCESS,
                  "Get thread-local storage",
                  ["u_info"])
        
        self._add(212, "lookup_dcookie", 3, SyscallCategory.FILE_IO,
                  "Get directory entry's path",
                  ["cookie64", "buf", "len"])
        
        self._add(213, "epoll_create", 1, SyscallCategory.FILE_IO,
                  "Create epoll file descriptor",
                  ["size"])
        
        self._add(214, "epoll_ctl_old", 4, SyscallCategory.FILE_IO,
                  "Control epoll file descriptor (obsolete)",
                  ["epfd", "op", "fd", "event"])
        
        self._add(215, "epoll_wait_old", 4, SyscallCategory.FILE_IO,
                  "Wait for epoll events (obsolete)",
                  ["epfd", "events", "maxevents", "timeout"])
        
        self._add(216, "remap_file_pages", 5, SyscallCategory.MEMORY,
                  "Create nonlinear file mapping",
                  ["start", "size", "prot", "pgoff", "flags"])
        
        self._add(217, "getdents64", 3, SyscallCategory.FILE_IO,
                  "Get directory entries (64-bit)",
                  ["fd", "dirent", "count"])
        
        self._add(218, "set_tid_address", 1, SyscallCategory.PROCESS,
                  "Set pointer to thread ID",
                  ["tidptr"])
        
        self._add(219, "restart_syscall", 0, SyscallCategory.SIGNAL,
                  "Restart system call after interruption",
                  [])
        
        self._add(220, "semtimedop", 4, SyscallCategory.IPC,
                  "Semaphore operations with timeout",
                  ["semid", "tsops", "nsops", "timeout"])
        
        self._add(221, "fadvise64", 4, SyscallCategory.FILE_IO,
                  "Predeclare access pattern for file data",
                  ["fd", "offset", "len", "advice"])
        
        self._add(222, "timer_create", 3, SyscallCategory.TIME,
                  "Create POSIX per-process timer",
                  ["which_clock", "timer_event_spec", "created_timer_id"])
        
        self._add(223, "timer_settime", 4, SyscallCategory.TIME,
                  "Arm/disarm POSIX per-process timer",
                  ["timer_id", "flags", "new_setting", "old_setting"])
        
        self._add(224, "timer_gettime", 2, SyscallCategory.TIME,
                  "Fetch state of POSIX per-process timer",
                  ["timer_id", "setting"])
        
        self._add(225, "timer_getoverrun", 1, SyscallCategory.TIME,
                  "Get overrun count for POSIX per-process timer",
                  ["timer_id"])
        
        self._add(226, "timer_delete", 1, SyscallCategory.TIME,
                  "Delete POSIX per-process timer",
                  ["timer_id"])
        
        self._add(227, "clock_settime", 2, SyscallCategory.TIME,
                  "Set clock time",
                  ["which_clock", "tp"])
        
        self._add(228, "clock_gettime", 2, SyscallCategory.TIME,
                  "Get clock time",
                  ["which_clock", "tp"])
        
        self._add(229, "clock_getres", 2, SyscallCategory.TIME,
                  "Get clock resolution",
                  ["which_clock", "tp"])
        
        self._add(230, "clock_nanosleep", 4, SyscallCategory.TIME,
                  "High-resolution sleep with clock selection",
                  ["which_clock", "flags", "rqtp", "rmtp"])
        
        self._add(231, "exit_group", 1, SyscallCategory.PROCESS,
                  "Exit all threads in process",
                  ["error_code"])
        
        self._add(232, "epoll_wait", 4, SyscallCategory.FILE_IO,
                  "Wait for epoll events",
                  ["epfd", "events", "maxevents", "timeout"])
        
        self._add(233, "epoll_ctl", 4, SyscallCategory.FILE_IO,
                  "Control epoll file descriptor",
                  ["epfd", "op", "fd", "event"])
        
        self._add(234, "tgkill", 3, SyscallCategory.SIGNAL,
                  "Send signal to specific thread",
                  ["tgid", "tid", "sig"])
        
        self._add(235, "utimes", 2, SyscallCategory.FILE_IO,
                  "Change file timestamps",
                  ["filename", "utimes"])
        
        self._add(236, "vserver", 0, SyscallCategory.SYSTEM,
                  "VServer (unimplemented)",
                  [])
        
        self._add(237, "mbind", 6, SyscallCategory.MEMORY,
                  "Set memory policy for range",
                  ["start", "len", "mode", "nmask", "maxnode", "flags"])
        
        self._add(238, "set_mempolicy", 3, SyscallCategory.MEMORY,
                  "Set default NUMA memory policy",
                  ["mode", "nmask", "maxnode"])
        
        self._add(239, "get_mempolicy", 5, SyscallCategory.MEMORY,
                  "Get NUMA memory policy",
                  ["policy", "nmask", "maxnode", "addr", "flags"])
        
        self._add(240, "mq_open", 4, SyscallCategory.IPC,
                  "Open message queue",
                  ["u_name", "oflag", "mode", "u_attr"])
        
        self._add(241, "mq_unlink", 1, SyscallCategory.IPC,
                  "Remove message queue",
                  ["u_name"])
        
        self._add(242, "mq_timedsend", 5, SyscallCategory.IPC,
                  "Send message to queue with timeout",
                  ["mqdes", "u_msg_ptr", "msg_len", "msg_prio", "u_abs_timeout"])
        
        self._add(243, "mq_timedreceive", 5, SyscallCategory.IPC,
                  "Receive message from queue with timeout",
                  ["mqdes", "u_msg_ptr", "msg_len", "u_msg_prio", "u_abs_timeout"])
        
        self._add(244, "mq_notify", 2, SyscallCategory.IPC,
                  "Register for notification when message available",
                  ["mqdes", "u_notification"])
        
        self._add(245, "mq_getsetattr", 3, SyscallCategory.IPC,
                  "Get/set message queue attributes",
                  ["mqdes", "u_mqstat", "u_omqstat"])
        
        self._add(246, "kexec_load", 4, SyscallCategory.SYSTEM,
                  "Load new kernel for later execution",
                  ["entry", "nr_segments", "segments", "flags"])
        
        self._add(247, "waitid", 5, SyscallCategory.PROCESS,
                  "Wait for process to change state",
                  ["which", "upid", "infop", "options", "ru"])
        
        self._add(248, "add_key", 5, SyscallCategory.SECURITY,
                  "Add key to kernel's key management",
                  ["_type", "_description", "_payload", "plen", "ringid"])
        
        self._add(249, "request_key", 4, SyscallCategory.SECURITY,
                  "Request key from kernel's key management",
                  ["_type", "_description", "_callout_info", "destringid"])
        
        self._add(250, "keyctl", 5, SyscallCategory.SECURITY,
                  "Manipulate kernel's key management",
                  ["option", "arg2", "arg3", "arg4", "arg5"])
        
        self._add(251, "ioprio_set", 3, SyscallCategory.PROCESS,
                  "Set I/O scheduling priority",
                  ["which", "who", "ioprio"])
        
        self._add(252, "ioprio_get", 2, SyscallCategory.PROCESS,
                  "Get I/O scheduling priority",
                  ["which", "who"])
        
        self._add(253, "inotify_init", 0, SyscallCategory.FILE_IO,
                  "Initialize inotify instance",
                  [])
        
        self._add(254, "inotify_add_watch", 3, SyscallCategory.FILE_IO,
                  "Add watch to inotify instance",
                  ["fd", "pathname", "mask"])
        
        self._add(255, "inotify_rm_watch", 2, SyscallCategory.FILE_IO,
                  "Remove watch from inotify instance",
                  ["fd", "wd"])
        
        self._add(256, "migrate_pages", 4, SyscallCategory.MEMORY,
                  "Move all pages in process to another set of nodes",
                  ["pid", "maxnode", "old_nodes", "new_nodes"])
        
        self._add(257, "openat", 4, SyscallCategory.FILE_IO,
                  "Open file relative to directory fd",
                  ["dfd", "filename", "flags", "mode"])
        
        self._add(258, "mkdirat", 3, SyscallCategory.FILE_IO,
                  "Create directory relative to directory fd",
                  ["dfd", "pathname", "mode"])
        
        self._add(259, "mknodat", 4, SyscallCategory.FILE_IO,
                  "Create special file relative to directory fd",
                  ["dfd", "filename", "mode", "dev"])
        
        self._add(260, "fchownat", 5, SyscallCategory.FILE_IO,
                  "Change ownership relative to directory fd",
                  ["dfd", "filename", "user", "group", "flag"])
        
        self._add(261, "futimesat", 3, SyscallCategory.FILE_IO,
                  "Change timestamps relative to directory fd",
                  ["dfd", "filename", "utimes"])
        
        self._add(262, "newfstatat", 4, SyscallCategory.FILE_IO,
                  "Get file status relative to directory fd",
                  ["dfd", "filename", "statbuf", "flag"])
        
        self._add(263, "unlinkat", 3, SyscallCategory.FILE_IO,
                  "Remove file relative to directory fd",
                  ["dfd", "pathname", "flag"])
        
        self._add(264, "renameat", 4, SyscallCategory.FILE_IO,
                  "Rename file relative to directory fds",
                  ["olddfd", "oldname", "newdfd", "newname"])
        
        self._add(265, "linkat", 5, SyscallCategory.FILE_IO,
                  "Create hard link relative to directory fds",
                  ["olddfd", "oldname", "newdfd", "newname", "flags"])
        
        self._add(266, "symlinkat", 3, SyscallCategory.FILE_IO,
                  "Create symbolic link relative to directory fd",
                  ["oldname", "newdfd", "newname"])
        
        self._add(267, "readlinkat", 4, SyscallCategory.FILE_IO,
                  "Read symbolic link relative to directory fd",
                  ["dfd", "pathname", "buf", "bufsiz"])
        
        self._add(268, "fchmodat", 3, SyscallCategory.FILE_IO,
                  "Change permissions relative to directory fd",
                  ["dfd", "filename", "mode"])
        
        self._add(269, "faccessat", 3, SyscallCategory.FILE_IO,
                  "Check permissions relative to directory fd",
                  ["dfd", "filename", "mode"])
        
        self._add(270, "pselect6", 6, SyscallCategory.FILE_IO,
                  "Synchronous I/O multiplexing with signal mask",
                  ["n", "inp", "outp", "exp", "tsp", "sig"])
        
        self._add(271, "ppoll", 5, SyscallCategory.FILE_IO,
                  "Wait for events on file descriptors with signal mask",
                  ["ufds", "nfds", "tsp", "sigmask", "sigsetsize"])
        
        self._add(272, "unshare", 1, SyscallCategory.PROCESS,
                  "Disassociate parts of process execution context",
                  ["unshare_flags"])
        
        self._add(273, "set_robust_list", 2, SyscallCategory.IPC,
                  "Set robust futex list",
                  ["head", "len"])
        
        self._add(274, "get_robust_list", 3, SyscallCategory.IPC,
                  "Get robust futex list",
                  ["pid", "head_ptr", "len_ptr"])
        
        self._add(275, "splice", 6, SyscallCategory.FILE_IO,
                  "Splice data to/from pipe",
                  ["fd_in", "off_in", "fd_out", "off_out", "len", "flags"])
        
        self._add(276, "tee", 4, SyscallCategory.FILE_IO,
                  "Duplicate pipe content",
                  ["fdin", "fdout", "len", "flags"])
        
        self._add(277, "sync_file_range", 4, SyscallCategory.FILE_IO,
                  "Sync file segment with disk",
                  ["fd", "offset", "nbytes", "flags"])
        
        self._add(278, "vmsplice", 4, SyscallCategory.FILE_IO,
                  "Splice user pages to pipe",
                  ["fd", "iov", "nr_segs", "flags"])
        
        self._add(279, "move_pages", 6, SyscallCategory.MEMORY,
                  "Move individual pages of process to another node",
                  ["pid", "nr_pages", "pages", "nodes", "status", "flags"])
        
        self._add(280, "utimensat", 4, SyscallCategory.FILE_IO,
                  "Change file timestamps with nanosecond precision",
                  ["dfd", "filename", "utimes", "flags"])
        
        self._add(281, "epoll_pwait", 6, SyscallCategory.FILE_IO,
                  "Wait for epoll events with signal mask",
                  ["epfd", "events", "maxevents", "timeout", "sigmask", "sigsetsize"])
        
        self._add(282, "signalfd", 3, SyscallCategory.SIGNAL,
                  "Create file descriptor for signal reception",
                  ["ufd", "user_mask", "sizemask"])
        
        self._add(283, "timerfd_create", 2, SyscallCategory.TIME,
                  "Create timer that delivers events via file descriptor",
                  ["clockid", "flags"])
        
        self._add(284, "eventfd", 1, SyscallCategory.FILE_IO,
                  "Create file descriptor for event notification",
                  ["count"])
        
        self._add(285, "fallocate", 4, SyscallCategory.FILE_IO,
                  "Manipulate file space",
                  ["fd", "mode", "offset", "len"])
        
        self._add(286, "timerfd_settime", 4, SyscallCategory.TIME,
                  "Arm/disarm timer via file descriptor",
                  ["ufd", "flags", "utmr", "otmr"])
        
        self._add(287, "timerfd_gettime", 2, SyscallCategory.TIME,
                  "Get current setting of timer via file descriptor",
                  ["ufd", "otmr"])
        
        self._add(288, "accept4", 4, SyscallCategory.NETWORK,
                  "Accept connection on socket with flags",
                  ["fd", "upeer_sockaddr", "upeer_addrlen", "flags"])
        
        self._add(289, "signalfd4", 4, SyscallCategory.SIGNAL,
                  "Create file descriptor for signal reception with flags",
                  ["ufd", "user_mask", "sizemask", "flags"])
        
        self._add(290, "eventfd2", 2, SyscallCategory.FILE_IO,
                  "Create file descriptor for event notification with flags",
                  ["count", "flags"])
        
        self._add(291, "epoll_create1", 1, SyscallCategory.FILE_IO,
                  "Create epoll file descriptor with flags",
                  ["flags"])
        
        self._add(292, "dup3", 3, SyscallCategory.FILE_IO,
                  "Duplicate file descriptor with flags",
                  ["oldfd", "newfd", "flags"])
        
        self._add(293, "pipe2", 2, SyscallCategory.IPC,
                  "Create pipe with flags",
                  ["fildes", "flags"])
        
        self._add(294, "inotify_init1", 1, SyscallCategory.FILE_IO,
                  "Initialize inotify instance with flags",
                  ["flags"])
        
        self._add(295, "preadv", 5, SyscallCategory.FILE_IO,
                  "Read data into multiple buffers at offset",
                  ["fd", "vec", "vlen", "pos_l", "pos_h"])
        
        self._add(296, "pwritev", 5, SyscallCategory.FILE_IO,
                  "Write data from multiple buffers at offset",
                  ["fd", "vec", "vlen", "pos_l", "pos_h"])
        
        self._add(297, "rt_tgsigqueueinfo", 4, SyscallCategory.SIGNAL,
                  "Queue signal and data to specific thread",
                  ["tgid", "pid", "sig", "uinfo"])
        
        self._add(298, "perf_event_open", 5, SyscallCategory.SYSTEM,
                  "Set up performance monitoring",
                  ["attr_uptr", "pid", "cpu", "group_fd", "flags"])
        
        self._add(299, "recvmmsg", 5, SyscallCategory.NETWORK,
                  "Receive multiple messages on socket",
                  ["fd", "mmsg", "vlen", "flags", "timeout"])
        
        self._add(300, "fanotify_init", 2, SyscallCategory.FILE_IO,
                  "Create and initialize fanotify group",
                  ["flags", "event_f_flags"])
        
        self._add(301, "fanotify_mark", 5, SyscallCategory.FILE_IO,
                  "Add/remove/flush marks from fanotify group",
                  ["fanotify_fd", "flags", "mask", "dfd", "pathname"])
        
        self._add(302, "prlimit64", 4, SyscallCategory.SYSTEM,
                  "Get/set resource limits",
                  ["pid", "resource", "new_rlim", "old_rlim"])
        
        self._add(303, "name_to_handle_at", 5, SyscallCategory.FILE_IO,
                  "Obtain handle for pathname",
                  ["dfd", "name", "handle", "mnt_id", "flag"])
        
        self._add(304, "open_by_handle_at", 3, SyscallCategory.FILE_IO,
                  "Open file via handle",
                  ["mountdirfd", "handle", "flags"])
        
        self._add(305, "clock_adjtime", 2, SyscallCategory.TIME,
                  "Tune kernel clock",
                  ["which_clock", "utx"])
        
        self._add(306, "syncfs", 1, SyscallCategory.FILE_IO,
                  "Sync filesystem containing file",
                  ["fd"])
        
        self._add(307, "sendmmsg", 4, SyscallCategory.NETWORK,
                  "Send multiple messages on socket",
                  ["fd", "mmsg", "vlen", "flags"])
        
        self._add(308, "setns", 2, SyscallCategory.PROCESS,
                  "Reassociate thread with namespace",
                  ["fd", "nstype"])
        
        self._add(309, "getcpu", 3, SyscallCategory.SYSTEM,
                  "Determine CPU and NUMA node",
                  ["cpup", "nodep", "unused"])
        
        self._add(310, "process_vm_readv", 6, SyscallCategory.MEMORY,
                  "Transfer data between process address spaces",
                  ["pid", "lvec", "liovcnt", "rvec", "riovcnt", "flags"])
        
        self._add(311, "process_vm_writev", 6, SyscallCategory.MEMORY,
                  "Transfer data between process address spaces",
                  ["pid", "lvec", "liovcnt", "rvec", "riovcnt", "flags"])
        
        self._add(312, "kcmp", 5, SyscallCategory.PROCESS,
                  "Compare two processes to determine if they share resource",
                  ["pid1", "pid2", "type", "idx1", "idx2"])
        
        self._add(313, "finit_module", 3, SyscallCategory.SYSTEM,
                  "Load kernel module from fd",
                  ["fd", "uargs", "flags"])
        
        self._add(314, "sched_setattr", 3, SyscallCategory.PROCESS,
                  "Set scheduling policy and attributes",
                  ["pid", "uattr", "flags"])
        
        self._add(315, "sched_getattr", 4, SyscallCategory.PROCESS,
                  "Get scheduling policy and attributes",
                  ["pid", "uattr", "size", "flags"])
        
        self._add(316, "renameat2", 5, SyscallCategory.FILE_IO,
                  "Rename file with flags",
                  ["olddfd", "oldname", "newdfd", "newname", "flags"])
        
        self._add(317, "seccomp", 3, SyscallCategory.SECURITY,
                  "Operate on Secure Computing state",
                  ["op", "flags", "uargs"])
        
        self._add(318, "getrandom", 3, SyscallCategory.SYSTEM,
                  "Obtain random bytes",
                  ["buf", "count", "flags"])
        
        self._add(319, "memfd_create", 2, SyscallCategory.MEMORY,
                  "Create anonymous file",
                  ["uname", "flags"])
        
        self._add(320, "kexec_file_load", 5, SyscallCategory.SYSTEM,
                  "Load new kernel from file for later execution",
                  ["kernel_fd", "initrd_fd", "cmdline_len", "cmdline_ptr", "flags"])
        
        self._add(321, "bpf", 3, SyscallCategory.SYSTEM,
                  "Perform command on extended BPF map or program",
                  ["cmd", "uattr", "size"])
        
        self._add(322, "execveat", 5, SyscallCategory.PROCESS,
                  "Execute program relative to directory fd",
                  ["fd", "filename", "argv", "envp", "flags"])
        
        self._add(323, "userfaultfd", 1, SyscallCategory.MEMORY,
                  "Create file descriptor for handling page faults in user space",
                  ["flags"])
        
        self._add(324, "membarrier", 2, SyscallCategory.MEMORY,
                  "Issue memory barriers on set of threads",
                  ["cmd", "flags"])
        
        self._add(325, "mlock2", 3, SyscallCategory.MEMORY,
                  "Lock memory pages with flags",
                  ["start", "len", "flags"])
        
        self._add(326, "copy_file_range", 6, SyscallCategory.FILE_IO,
                  "Copy range of data from one file to another",
                  ["fd_in", "off_in", "fd_out", "off_out", "len", "flags"])
        
        self._add(327, "preadv2", 6, SyscallCategory.FILE_IO,
                  "Read data into multiple buffers with flags",
                  ["fd", "vec", "vlen", "pos_l", "pos_h", "flags"])
        
        self._add(328, "pwritev2", 6, SyscallCategory.FILE_IO,
                  "Write data from multiple buffers with flags",
                  ["fd", "vec", "vlen", "pos_l", "pos_h", "flags"])
        
        self._add(329, "pkey_mprotect", 4, SyscallCategory.MEMORY,
                  "Set protection on memory region with key",
                  ["start", "len", "prot", "pkey"])
        
        self._add(330, "pkey_alloc", 2, SyscallCategory.MEMORY,
                  "Allocate protection key",
                  ["flags", "init_val"])
        
        self._add(331, "pkey_free", 1, SyscallCategory.MEMORY,
                  "Free protection key",
                  ["pkey"])
        
        self._add(332, "statx", 5, SyscallCategory.FILE_IO,
                  "Get file status (extended)",
                  ["dfd", "filename", "flags", "mask", "buffer"])
        
        self._add(333, "io_pgetevents", 6, SyscallCategory.FILE_IO,
                  "Read asynchronous I/O events with signal mask",
                  ["ctx_id", "min_nr", "nr", "events", "timeout", "usig"])
        
        self._add(334, "rseq", 4, SyscallCategory.PROCESS,
                  "Restartable sequences",
                  ["rseq", "rseq_len", "flags", "sig"])
        
        # 335-423 are reserved for future use or architecture-specific
        
        self._add(424, "pidfd_send_signal", 4, SyscallCategory.SIGNAL,
                  "Send signal to process via pidfd",
                  ["pidfd", "sig", "info", "flags"])
        
        self._add(425, "io_uring_setup", 2, SyscallCategory.FILE_IO,
                  "Setup io_uring context",
                  ["entries", "params"])
        
        self._add(426, "io_uring_enter", 6, SyscallCategory.FILE_IO,
                  "Initiate and complete I/O using io_uring",
                  ["fd", "to_submit", "min_complete", "flags", "sig", "sigsz"])
        
        self._add(427, "io_uring_register", 4, SyscallCategory.FILE_IO,
                  "Register files or buffers with io_uring instance",
                  ["fd", "opcode", "arg", "nr_args"])
        
        self._add(428, "open_tree", 3, SyscallCategory.FILE_IO,
                  "Pick/create mount object",
                  ["dfd", "filename", "flags"])
        
        self._add(429, "move_mount", 5, SyscallCategory.FILE_IO,
                  "Move mount object",
                  ["from_dfd", "from_pathname", "to_dfd", "to_pathname", "flags"])
        
        self._add(430, "fsopen", 2, SyscallCategory.FILE_IO,
                  "Open filesystem configuration context",
                  ["fsname", "flags"])
        
        self._add(431, "fsconfig", 5, SyscallCategory.FILE_IO,
                  "Configure filesystem",
                  ["fd", "cmd", "key", "value", "aux"])
        
        self._add(432, "fsmount", 3, SyscallCategory.FILE_IO,
                  "Create mount from filesystem configuration context",
                  ["fd", "flags", "attr_flags"])
        
        self._add(433, "fspick", 3, SyscallCategory.FILE_IO,
                  "Pick existing mount for reconfiguration",
                  ["dfd", "path", "flags"])
        
        self._add(434, "pidfd_open", 2, SyscallCategory.PROCESS,
                  "Obtain file descriptor referring to process",
                  ["pid", "flags"])
        
        self._add(435, "clone3", 2, SyscallCategory.PROCESS,
                  "Create child process (extended)",
                  ["uargs", "size"])
        
        self._add(436, "close_range", 3, SyscallCategory.FILE_IO,
                  "Close range of file descriptors",
                  ["fd", "max_fd", "flags"])
        
        self._add(437, "openat2", 4, SyscallCategory.FILE_IO,
                  "Open file relative to directory fd (extended)",
                  ["dfd", "filename", "how", "usize"])
        
        self._add(438, "pidfd_getfd", 3, SyscallCategory.PROCESS,
                  "Get file descriptor from another process",
                  ["pidfd", "fd", "flags"])
        
        self._add(439, "faccessat2", 4, SyscallCategory.FILE_IO,
                  "Check permissions with flags",
                  ["dfd", "filename", "mode", "flags"])
        
        self._add(440, "process_madvise", 5, SyscallCategory.MEMORY,
                  "Give advice about use of memory to another process",
                  ["pidfd", "vec", "vlen", "behavior", "flags"])
        
        self._add(441, "epoll_pwait2", 6, SyscallCategory.FILE_IO,
                  "Wait for epoll events with timeout",
                  ["epfd", "events", "maxevents", "timeout", "sigmask", "sigsetsize"])
        
        self._add(442, "mount_setattr", 5, SyscallCategory.FILE_IO,
                  "Change mount properties",
                  ["dfd", "path", "flags", "uattr", "usize"])
        
        self._add(443, "quotactl_fd", 4, SyscallCategory.FILE_IO,
                  "Manipulate disk quotas via fd",
                  ["fd", "cmd", "id", "addr"])
        
        self._add(444, "landlock_create_ruleset", 3, SyscallCategory.SECURITY,
                  "Create Landlock ruleset",
                  ["attr", "size", "flags"])
        
        self._add(445, "landlock_add_rule", 4, SyscallCategory.SECURITY,
                  "Add rule to Landlock ruleset",
                  ["ruleset_fd", "rule_type", "rule_attr", "flags"])
        
        self._add(446, "landlock_restrict_self", 2, SyscallCategory.SECURITY,
                  "Enforce Landlock ruleset",
                  ["ruleset_fd", "flags"])
        
        self._add(447, "memfd_secret", 1, SyscallCategory.MEMORY,
                  "Create secret memory area",
                  ["flags"])
        
        self._add(448, "process_mrelease", 2, SyscallCategory.MEMORY,
                  "Release memory of dying process",
                  ["pidfd", "flags"])
        
        self._add(449, "futex_waitv", 5, SyscallCategory.IPC,
                  "Wait on multiple futexes",
                  ["waiters", "nr_futexes", "flags", "timeout", "clockid"])
        
        self._add(450, "set_mempolicy_home_node", 4, SyscallCategory.MEMORY,
                  "Set home node for MPOL_BIND memory policy",
                  ["start", "len", "home_node", "flags"])       
        
        
        
    def _add(self, number: int, name: str, num_args: int, 
             category: SyscallCategory, description: str, arg_names: List[str]):
        """Add a syscall to the table"""
        syscall = SyscallDescriptor(
            number=number,
            name=name,
            num_args=num_args,
            category=category,
            description=description,
            arg_names=arg_names
        )
        self.syscalls[number] = syscall
        self.syscalls_by_name[name] = syscall
    
    def get_by_number(self, number: int) -> Optional[SyscallDescriptor]:
        """Get syscall descriptor by number"""
        return self.syscalls.get(number)
    
    def get_by_name(self, name: str) -> Optional[SyscallDescriptor]:
        """Get syscall descriptor by name"""
        return self.syscalls_by_name.get(name)
    
    def list_by_category(self, category: SyscallCategory) -> List[SyscallDescriptor]:
        """List all syscalls in a category"""
        return [sc for sc in self.syscalls.values() if sc.category == category]
    
    def generate_test_for_syscall(self, syscall: SyscallDescriptor) -> str:
        """Generate AILANG test code for a syscall"""
        # This will be used to generate the test suite
        pass


# Global syscall table instance
LINUX_X64_SYSCALLS = LinuxX86_64SyscallTable()


def print_syscall_reference():
    """Print formatted syscall reference"""
    table = LINUX_X64_SYSCALLS
    
    for category in SyscallCategory:
        syscalls = table.list_by_category(category)
        if syscalls:
            print(f"\n{'='*70}")
            print(f"  {category.name} ({len(syscalls)} syscalls)")
            print(f"{'='*70}")
            for sc in sorted(syscalls, key=lambda x: x.number):
                print(f"  {sc.number:3d}  {sc}")


if __name__ == "__main__":
    print_syscall_reference()