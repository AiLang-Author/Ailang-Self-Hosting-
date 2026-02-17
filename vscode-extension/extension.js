const vscode = require('vscode');
const cp = require('child_process');
const path = require('path');
const fs = require('fs');

let diagnosticCollection;
const symbolCache = new Map();

// =============================================================================
// AILANG KEYWORD + BUILTIN LISTS (for completion)
// =============================================================================
const KEYWORDS = [
    'IfCondition', 'ThenBlock', 'ElseBlock', 'WhileLoop', 'ForEvery', 'in',
    'BreakLoop', 'ContinueLoop', 'ReturnValue', 'ProcessExit', 'RunTask',
    'HaltProgram', 'TryBlock', 'CatchError', 'FinallyBlock', 'Branch', 'Fork',
    'TrueBlock', 'FalseBlock', 'ChoosePath', 'CaseOption', 'DefaultOption',
    'Function', 'SubRoutine', 'Combinator', 'MacroBlock', 'Lambda',
    'LibraryImport', 'FixedPool', 'DynamicPool', 'TemporalPool', 'NeuralPool',
    'KernelPool', 'ActorPool', 'SecurityPool', 'ConstrainedPool', 'FilePool',
    'LinkagePool', 'SubPool', 'Input', 'Output', 'Body', 'Where',
    'Initialize', 'CanChange', 'CanBeNull', 'Range', 'MaximumLength',
    'MinimumLength', 'ElementType', 'PointerTo', 'Direction', 'Type',
    'True', 'False', 'Null', 'PI', 'E', 'PHI',
    'Integer', 'FloatingPoint', 'Text', 'Boolean', 'Address', 'Void', 'Any',
    'Byte', 'Word', 'DWord', 'QWord', 'Array', 'Map', 'Tuple', 'Record',
    'LoopMain', 'LoopActor', 'LoopStart', 'AcronymDefinitions', 'Constant'
];

const BUILTINS = [
    // Math
    'Add', 'Subtract', 'Multiply', 'Divide', 'Modulo', 'Power', 'Negate',
    'Increment', 'Decrement', 'AbsoluteValue', 'SquareRoot', 'Floor', 'Ceil',
    'Round', 'Min', 'Max', 'Clamp', 'Sign', 'Lerp', 'Sin', 'Cos', 'Tan',
    'Exp', 'Log', 'Log2', 'Log10', 'FusedMultiplyAdd', 'Hypotenuse',
    // Comparison
    'EqualTo', 'NotEqual', 'LessThan', 'GreaterThan', 'LessEqual', 'GreaterEqual',
    // Logic
    'And', 'Or', 'Not', 'Xor', 'Implies',
    // Bitwise
    'BitwiseAnd', 'BitwiseOr', 'BitwiseXor', 'BitwiseNot', 'LeftShift', 'RightShift',
    'PopCount', 'CountLeadingZeros', 'CountTrailingZeros', 'RotateLeft', 'RotateRight',
    // Memory
    'Allocate', 'Deallocate', 'GetByte', 'SetByte', 'MemoryCopy', 'MemorySet',
    'MemoryCompare', 'Dereference', 'StoreValue', 'AddressOf', 'SizeOf',
    // Linkage
    'AllocateLinkage', 'FreeLinkage', 'CopyLinkage', 'CopyLinkageInto',
    'ResetLinkage', 'CompareLinkage', 'PoolSize', 'PoolFieldCount', 'PoolFieldOffset',
    // I/O
    'PrintMessage', 'PrintNumber', 'PrintString', 'PrintChar',
    'ReadInput', 'ReadInputNumber', 'GetUserChoice', 'ReadKey',
    // Strings
    'StringLength', 'StringCompare', 'StringCopy', 'StringConcat',
    'StringEquals', 'StringContains', 'StringStartsWith', 'StringEndsWith',
    'StringSubstring', 'StringToUpper', 'StringToLower', 'StringTrim',
    'StringReplace', 'NumberToString', 'StringToNumber', 'StringFromChar',
    'StringIndexOf', 'StringExtract', 'StringExtractUntil', 'StringSplit',
    // File
    'ReadTextFile', 'WriteTextFile', 'AppendTextFile', 'FileExists',
    'OpenFile', 'CloseFile', 'ReadFile', 'WriteFile', 'SeekPosition',
    'FlushFile', 'GetFileSize', 'CreateDirectory', 'ListDirectory',
    // System
    'SystemCall', 'ProcessExit', 'RunTask', 'HaltProgram',
    // Debug
    'DebugAssert', 'DebugTrace', 'DebugBreak', 'DebugMemory', 'DebugPerf', 'DebugInspect'
];

// =============================================================================
// SHORTHAND ALIAS MAP — type short, disk stays canonical
// =============================================================================
const ALIASES = {
    // Comparison
    'GT':  'GreaterThan',
    'LT':  'LessThan',
    'GE':  'GreaterEqual',
    'LE':  'LessEqual',
    'EQ':  'EqualTo',
    'NE':  'NotEqual',
    // Control flow
    'IC':  'IfCondition',
    'TB':  'ThenBlock',
    'EB':  'ElseBlock',
    'WL':  'WhileLoop',
    'FE':  'ForEvery',
    'BL':  'BreakLoop',
    'CL':  'ContinueLoop',
    'RV':  'ReturnValue',
    'CP':  'ChoosePath',
    'CO':  'CaseOption',
    'DO':  'DefaultOption',
    // Definitions
    'FN':  'Function',
    'SR':  'SubRoutine',
    'CB':  'Combinator',
    'LM':  'Lambda',
    'MB':  'MacroBlock',
    'LI':  'LibraryImport',
    // Pools
    'FP':  'FixedPool',
    'DP':  'DynamicPool',
    'TP':  'TemporalPool',
    'NP':  'NeuralPool',
    'KP':  'KernelPool',
    'AP':  'ActorPool',
    'SP':  'SecurityPool',
    'XP':  'ConstrainedPool',
    'FLP': 'FilePool',
    'LP':  'LinkagePool',
    'SUB': 'SubPool',
    // Types
    'INT': 'Integer',
    'FLT': 'FloatingPoint',
    'TXT': 'Text',
    'BOL': 'Boolean',
    'ADR': 'Address',
    'ARR': 'Array',
    // Logic
    'BA':  'BitwiseAnd',
    'BO':  'BitwiseOr',
    'BX':  'BitwiseXor',
    'BN':  'BitwiseNot',
    'LS':  'LeftShift',
    'RS':  'RightShift',
    // Memory
    'ALLOC': 'Allocate',
    'DEALLOC': 'Deallocate',
    'GB':  'GetByte',
    'SB':  'SetByte',
    'MCPY': 'MemoryCopy',
    'MSET': 'MemorySet',
    'DEREF': 'Dereference',
    'ADDR': 'AddressOf',
    'SZOF': 'SizeOf',
    // I/O
    'PM':  'PrintMessage',
    'PN':  'PrintNumber',
    'PS':  'PrintString',
    'PC':  'PrintChar',
    'RI':  'ReadInput',
    'RIN': 'ReadInputNumber',
    // String
    'SLEN': 'StringLength',
    'SCMP': 'StringCompare',
    'SCAT': 'StringConcat',
    'SEQ':  'StringEquals',
    'SSUB': 'StringSubstring',
    // Error handling
    'TRY': 'TryBlock',
    'CAT': 'CatchError',
    'FIN': 'FinallyBlock',
    // Loop constructs
    'LMAIN': 'LoopMain',
    'LACT':  'LoopActor',
    'LSTART': 'LoopStart',
    // System
    'SC':  'SystemCall',
    'PE':  'ProcessExit',
    'RT':  'RunTask',
    'HP':  'HaltProgram',
    // Debug
    'DA':  'DebugAssert',
    'DT':  'DebugTrace',
    'DB':  'DebugBreak',
    'DM':  'DebugMemory',
    'DPF': 'DebugPerf',
    'DI':  'DebugInspect',
    // Math
    'ABS': 'AbsoluteValue',
    'SQRT': 'SquareRoot',
    'FMA': 'FusedMultiplyAdd',
    'HYPOT': 'Hypotenuse',
    'MOD': 'Modulo',
    'POW': 'Power',
    'NEG': 'Negate',
    'INC': 'Increment',
    'DEC': 'Decrement',
};

// Reverse lookup for display: "GreaterThan" -> "GT"
const REVERSE_ALIASES = {};
Object.entries(ALIASES).forEach(([short, canon]) => {
    if (!REVERSE_ALIASES[canon]) REVERSE_ALIASES[canon] = [];
    REVERSE_ALIASES[canon].push(short);
});

// =============================================================================
// SCAFFOLD TEMPLATES — type "Function." and get a ready-to-fill skeleton
// =============================================================================
const SCAFFOLDS = {
    'Function': {
        label: 'Function',
        detail: 'New function with Input/Output/Body',
        snippet: [
            'Function.${1:Name} {',
            '    Input: ${2:x}: ${3:Integer}',
            '    Output: ${4:Integer}',
            '    Body: {',
            '        ${5:// implementation}',
            '        ReturnValue(${6:result})',
            '    }',
            '}'
        ].join('\n')
    },
    'SubRoutine': {
        label: 'SubRoutine',
        detail: 'New subroutine with Input/Body',
        snippet: [
            'SubRoutine.${1:Name} {',
            '    Input: ${2:x}: ${3:Integer}',
            '    Body: {',
            '        ${4:// implementation}',
            '    }',
            '}'
        ].join('\n')
    },
    'Combinator': {
        label: 'Combinator',
        detail: 'New combinator with Input/Output/Body/Where',
        snippet: [
            'Combinator.${1:Name} {',
            '    Input: ${2:x}: ${3:Integer}',
            '    Output: ${4:Integer}',
            '    Body: {',
            '        ${5:// implementation}',
            '        ReturnValue(${6:result})',
            '    }',
            '    Where: {',
            '        ${7:// constraints}',
            '    }',
            '}'
        ].join('\n')
    },
    'FixedPool': {
        label: 'FixedPool',
        detail: 'New fixed-size pool',
        snippet: [
            'FixedPool.${1:Name} {',
            '    ${2:field1}: ${3:Integer}',
            '    ${4:field2}: ${5:Address}',
            '}'
        ].join('\n')
    },
    'DynamicPool': {
        label: 'DynamicPool',
        detail: 'New dynamic pool',
        snippet: [
            'DynamicPool.${1:Name} {',
            '    ${2:field1}: ${3:Integer}',
            '    ${4:field2}: ${5:Address}',
            '}'
        ].join('\n')
    },
    'LinkagePool': {
        label: 'LinkagePool',
        detail: 'New linkage pool (struct-like)',
        snippet: [
            'LinkagePool.${1:Name} {',
            '    ${2:field1}: ${3:Integer}',
            '    ${4:field2}: ${5:Address}',
            '}'
        ].join('\n')
    },
    'TemporalPool': {
        label: 'TemporalPool',
        detail: 'New temporal pool',
        snippet: [
            'TemporalPool.${1:Name} {',
            '    ${2:field1}: ${3:Integer}',
            '}'
        ].join('\n')
    },
    'NeuralPool': {
        label: 'NeuralPool',
        detail: 'New neural pool',
        snippet: [
            'NeuralPool.${1:Name} {',
            '    ${2:field1}: ${3:Integer}',
            '}'
        ].join('\n')
    },
    'KernelPool': {
        label: 'KernelPool',
        detail: 'New kernel pool',
        snippet: [
            'KernelPool.${1:Name} {',
            '    ${2:field1}: ${3:Integer}',
            '}'
        ].join('\n')
    },
    'ActorPool': {
        label: 'ActorPool',
        detail: 'New actor pool',
        snippet: [
            'ActorPool.${1:Name} {',
            '    ${2:field1}: ${3:Integer}',
            '}'
        ].join('\n')
    },
    'SecurityPool': {
        label: 'SecurityPool',
        detail: 'New security pool',
        snippet: [
            'SecurityPool.${1:Name} {',
            '    ${2:field1}: ${3:Integer}',
            '}'
        ].join('\n')
    },
    'ConstrainedPool': {
        label: 'ConstrainedPool',
        detail: 'New constrained pool with Where clause',
        snippet: [
            'ConstrainedPool.${1:Name} {',
            '    ${2:field1}: ${3:Integer}',
            '    Where: {',
            '        Range(${2:field1}, ${4:0}, ${5:100})',
            '    }',
            '}'
        ].join('\n')
    },
    'FilePool': {
        label: 'FilePool',
        detail: 'New file pool',
        snippet: [
            'FilePool.${1:Name} {',
            '    ${2:field1}: ${3:Address}',
            '}'
        ].join('\n')
    },
    'Lambda': {
        label: 'Lambda',
        detail: 'New lambda expression',
        snippet: [
            'Lambda.${1:Name} {',
            '    Input: ${2:x}: ${3:Integer}',
            '    Output: ${4:Integer}',
            '    Body: { ReturnValue(${5:x}) }',
            '}'
        ].join('\n')
    },
    'IfCondition': {
        label: 'IfCondition',
        detail: 'If/Then/Else block',
        snippet: [
            'IfCondition ${1:condition} ThenBlock: {',
            '    ${2:// then}',
            '} ElseBlock: {',
            '    ${3:// else}',
            '}'
        ].join('\n')
    },
    'WhileLoop': {
        label: 'WhileLoop',
        detail: 'While loop block',
        snippet: [
            'WhileLoop ${1:condition} {',
            '    ${2:// body}',
            '}'
        ].join('\n')
    },
    'ForEvery': {
        label: 'ForEvery',
        detail: 'For-each loop',
        snippet: [
            'ForEvery ${1:item} in ${2:collection} {',
            '    ${3:// body}',
            '}'
        ].join('\n')
    },
    'ChoosePath': {
        label: 'ChoosePath',
        detail: 'Switch/case block',
        snippet: [
            'ChoosePath(${1:value}) {',
            '    CaseOption ${2:1}: {',
            '        ${3:// handler}',
            '    }',
            '    DefaultOption: {',
            '        ${4:// default}',
            '    }',
            '}'
        ].join('\n')
    },
    'TryBlock': {
        label: 'TryBlock',
        detail: 'Try/Catch/Finally block',
        snippet: [
            'TryBlock: {',
            '    ${1:// risky code}',
            '} CatchError: {',
            '    ${2:// error handling}',
            '} FinallyBlock: {',
            '    ${3:// cleanup}',
            '}'
        ].join('\n')
    },
    'LoopMain': {
        label: 'LoopMain',
        detail: 'Main event loop',
        snippet: [
            'LoopMain {',
            '    ${1:// main loop body}',
            '}'
        ].join('\n')
    },
    'LoopActor': {
        label: 'LoopActor',
        detail: 'Actor event loop',
        snippet: [
            'LoopActor.${1:Name} {',
            '    ${2:// actor loop body}',
            '}'
        ].join('\n')
    },
    'LibraryImport': {
        label: 'LibraryImport',
        detail: 'Import a library',
        snippet: 'LibraryImport("${1:Library.Name}")'
    },
    'AcronymDefinitions': {
        label: 'AcronymDefinitions',
        detail: 'Acronym definition block',
        snippet: [
            'AcronymDefinitions {',
            '    ${1:ABBR} = "${2:Full Name}"',
            '}'
        ].join('\n')
    },
};

// =============================================================================
// SYMBOL KIND MAPPING (expanded for all Phase 1 kinds)
// =============================================================================
function mapSymbolKind(kindStr) {
    switch (kindStr) {
        case 'Function':        return vscode.SymbolKind.Function;
        case 'SubRoutine':      return vscode.SymbolKind.Method;
        case 'Combinator':      return vscode.SymbolKind.Function;
        case 'Lambda':          return vscode.SymbolKind.Function;
        case 'Parameter':       return vscode.SymbolKind.Variable;
        case 'Output':          return vscode.SymbolKind.TypeParameter;
        case 'FixedPool':       return vscode.SymbolKind.Struct;
        case 'DynamicPool':     return vscode.SymbolKind.Struct;
        case 'TemporalPool':    return vscode.SymbolKind.Struct;
        case 'NeuralPool':      return vscode.SymbolKind.Struct;
        case 'KernelPool':      return vscode.SymbolKind.Struct;
        case 'ActorPool':       return vscode.SymbolKind.Struct;
        case 'SecurityPool':    return vscode.SymbolKind.Struct;
        case 'ConstrainedPool': return vscode.SymbolKind.Struct;
        case 'FilePool':        return vscode.SymbolKind.Struct;
        case 'LinkagePool':     return vscode.SymbolKind.Class;
        case 'SubPool':         return vscode.SymbolKind.Struct;
        case 'Field':           return vscode.SymbolKind.Field;
        case 'Import':          return vscode.SymbolKind.Module;
        case 'Module':          return vscode.SymbolKind.Module;
        case 'Export':          return vscode.SymbolKind.Interface;
        case 'LoopMain':        return vscode.SymbolKind.Event;
        case 'LoopActor':       return vscode.SymbolKind.Event;
        case 'LoopStart':       return vscode.SymbolKind.Event;
        case 'Macro':           return vscode.SymbolKind.Constant;
        case 'AcronymDefs':     return vscode.SymbolKind.Namespace;
        case 'Variable':        return vscode.SymbolKind.Variable;
        default:                return vscode.SymbolKind.Variable;
    }
}

// =============================================================================
// WSL PATH HELPERS (Windows <-> Linux path translation)
// =============================================================================
const isWindows = process.platform === 'win32';

function toWslPath(winPath) {
    if (!isWindows || !winPath) return winPath;
    // C:\Users\Sean\file.ailang -> /mnt/c/Users/Sean/file.ailang
    return winPath
        .replace(/^([a-zA-Z]):/, (_, letter) => '/mnt/' + letter.toLowerCase())
        .replace(/\\/g, '/');
}



function wslExec(linuxCmd, callback) {
    if (isWindows) {
        // execFile bypasses cmd.exe entirely — no shell interpretation on Windows side
        // Arguments go directly to wsl.exe as an argv array
        cp.execFile('wsl.exe', ['bash', '-c', linuxCmd], { maxBuffer: 1024 * 1024 * 5 }, callback);
    } else {
        cp.exec(linuxCmd, { maxBuffer: 1024 * 1024 * 5 }, callback);
    }
}

// --- Top-level helper: resolve an AILang module name to a file path ---
function resolveAilangModule(moduleName, document) {
    // moduleName examples:
    //   "XArrays"                              -> Librarys/Library.XArrays.ailang
    //   "Compiler.Frontend.Lexer.CLexerMain"   -> Librarys/Compiler/Frontend/Lexer/Library.CLexerMain.ailang
    //   "Compiler.Import.CFileMap"             -> Librarys/Compiler/Import/Library.CFileMap.ailang
    //   "Analyzer"                             -> Librarys/Library.Analyzer.ailang
    //   "JSON"                                 -> Librarys/Library.JSON.ailang

    const docDir = path.dirname(document.fileName);

    // Split on dots: "Compiler.Frontend.Lexer.CLexerMain" -> ["Compiler","Frontend","Lexer","CLexerMain"]
    const parts = moduleName.split('.');

    // Build candidate paths from most specific to least
    const candidates = [];

    if (parts.length === 1) {
        // Simple name like "XArrays", "Analyzer", "JSON"
        candidates.push(path.join(docDir, 'Librarys', 'Library.' + parts[0] + '.ailang'));
        candidates.push(path.join(docDir, 'Librarys', parts[0] + '.ailang'));
        candidates.push(path.join(docDir, parts[0] + '.ailang'));
    } else {
        // Dotted path: dirs are all but last, filename is last
        // "Compiler.Frontend.Lexer.CLexerMain" -> Librarys/Compiler/Frontend/Lexer/Library.CLexerMain.ailang
        const dirs = parts.slice(0, -1);
        const file = parts[parts.length - 1];
        const dirPath = dirs.join(path.sep);

        // Primary: Librarys/<dirs>/Library.<file>.ailang
        candidates.push(path.join(docDir, 'Librarys', dirPath, 'Library.' + file + '.ailang'));
        // Alt: Librarys/<dirs>/<file>.ailang
        candidates.push(path.join(docDir, 'Librarys', dirPath, file + '.ailang'));
        // Alt: Librarys/Library.<all dots replaced>.ailang (flat naming)
        candidates.push(path.join(docDir, 'Librarys', 'Library.' + moduleName.replace(/\./g, '.') + '.ailang'));
        // Alt: just replace dots with path separators
        candidates.push(path.join(docDir, 'Librarys', moduleName.replace(/\./g, path.sep) + '.ailang'));
        // Alt: relative to doc dir
        candidates.push(path.join(docDir, dirPath, 'Library.' + file + '.ailang'));
        candidates.push(path.join(docDir, moduleName.replace(/\./g, path.sep) + '.ailang'));
    }

    for (const c of candidates) {
        if (fs.existsSync(c)) return c;
    }
    return null;
}

// =============================================================================
// ACTIVATION
// =============================================================================
function activate(context) {
    console.log('AILang extension active (Phase 2)');

    // Force .ailang file association — works around VS Code caching files as Plain Text
    const config = vscode.workspace.getConfiguration('files');
    const assoc = config.get('associations') || {};
    if (!assoc['*.ailang']) {
        assoc['*.ailang'] = 'ailang';
        config.update('associations', assoc, vscode.ConfigurationTarget.Global);
    }


    diagnosticCollection = vscode.languages.createDiagnosticCollection('ailang');
    context.subscriptions.push(diagnosticCollection);
    const flowLog = vscode.window.createOutputChannel('AILang Flow Debug');

    // Run on save
    context.subscriptions.push(vscode.workspace.onDidSaveTextDocument(doc => {
        if (doc.languageId === 'ailang') runLsp(doc);
    }));

    // Run on open
    context.subscriptions.push(vscode.workspace.onDidOpenTextDocument(doc => {
        if (doc.languageId === 'ailang') runLsp(doc);
    }));

    // ─── Command: Compile ────────────────────────────────────────────
    context.subscriptions.push(vscode.commands.registerCommand('ailang.compile', () => {
        const e = vscode.window.activeTextEditor;
        if (!e || e.document.languageId !== 'ailang') {
            vscode.window.showErrorMessage('Open an AILang file to compile.');
            return;
        }
        e.document.save().then(() => {
            const comp = toWslPath(path.join(__dirname, 'ailang.x'));
            const src = toWslPath(e.document.fileName);
            const srcDir = toWslPath(path.dirname(e.document.fileName));
            const out = src.replace(/\.[^/.]+$/, '') + '.x';
            const shellPath = isWindows ? 'wsl.exe' : '/bin/bash';
            const t = vscode.window.createTerminal({ name: 'AILang Build', shellPath });
            t.show();
            t.sendText(`cd "${srcDir}" && chmod +x "${comp}" && "${comp}" "${src}" "${out}"`);
        });
    }));

    // ─── Command: Run ────────────────────────────────────────────────
    context.subscriptions.push(vscode.commands.registerCommand('ailang.run', () => {
        const e = vscode.window.activeTextEditor;
        if (!e || e.document.languageId !== 'ailang') {
            vscode.window.showErrorMessage('Open an AILang file to run.');
            return;
        }
        e.document.save().then(() => {
            const comp = toWslPath(path.join(__dirname, 'ailang.x'));
            const src = toWslPath(e.document.fileName);
            const srcDir = toWslPath(path.dirname(e.document.fileName));
            const out = src.replace(/\.[^/.]+$/, '') + '.x';
            const shellPath = isWindows ? 'wsl.exe' : '/bin/bash';
            const t = vscode.window.createTerminal({ name: 'AILang Run', shellPath });
            t.show();
            t.sendText(`cd "${srcDir}" && chmod +x "${comp}" && "${comp}" "${src}" "${out}" && chmod +x "${out}" && "${out}"`);
        });
    }));

    // ─── Command: Analyze ────────────────────────────────────────────
    context.subscriptions.push(vscode.commands.registerCommand('ailang.analyze', () => {
        const e = vscode.window.activeTextEditor;
        if (!e || e.document.languageId !== 'ailang') return;
        runLsp(e.document);
        vscode.window.showInformationMessage('AILang: Analysis complete — check Problems panel.');
    }));

    // ─── Command: Open Docs ──────────────────────────────────────────
    context.subscriptions.push(vscode.commands.registerCommand('ailang.openDocs', () => {
        const docsPath = path.join(__dirname, 'docs');
        if (!fs.existsSync(docsPath)) {
            vscode.window.showErrorMessage('Documentation folder not found.');
            return;
        }
        fs.readdir(docsPath, (err, files) => {
            if (err) { vscode.window.showErrorMessage('Unable to read docs.'); return; }
            const manuals = files.filter(f => f.toLowerCase().endsWith('.md'));
            vscode.window.showQuickPick(manuals, { placeHolder: 'Select Manual' }).then(sel => {
                if (sel) vscode.commands.executeCommand('markdown.showPreview', vscode.Uri.file(path.join(docsPath, sel)));
            });
        });
    }));

    // ─── Command: Show Flow Graph (enhanced) ─────────────────────────
    context.subscriptions.push(vscode.commands.registerCommand('ailang.showFlow', () => {
        const e = vscode.window.activeTextEditor;
        if (!e) return;

        const panel = vscode.window.createWebviewPanel(
            'ailangFlow',
            'Connectome: ' + path.basename(e.document.fileName),
            vscode.ViewColumn.Two,
            { enableScripts: true, retainContextWhenHidden: true }
        );

        let refreshTimer = null;

        const updateGraph = () => {
            runTool(e.document, (err, data) => {
                if (err || !data || !data.symbols) {
                    panel.webview.html = getConnectomeHTML(null, e.document.uri.toString());
                    return;
                }
                symbolCache.set(e.document.uri.toString(), data);
                panel.webview.html = getConnectomeHTML(data, e.document.uri.toString());
            });
        };

        updateGraph();

        // Handle messages from webview
        panel.webview.onDidReceiveMessage(msg => {
            if (msg.type === 'goto') {
                // Check if this is an import node — if so, open the file
                if (msg.id) {
                    const data = symbolCache.get(e.document.uri.toString());
                    if (data && data.imports) {
                        const imp = data.imports.find(i => i.name === msg.id);
                        if (imp) {
                            // This is an import — resolve and open the file
                            const resolved = resolveAilangModule(imp.name, e.document);
                            if (resolved) {
                                vscode.workspace.openTextDocument(resolved).then(doc => {
                                    vscode.window.showTextDocument(doc, vscode.ViewColumn.One);
                                });
                                return;
                            }
                            // Couldn't resolve — fall through to goto line
                        }
                    }
                }

                // Default: jump to line in current file
                const line = Math.max(0, (msg.line || 1) - 1);
                const range = new vscode.Range(line, 0, line, 0);
                vscode.window.showTextDocument(e.document, { selection: range, viewColumn: vscode.ViewColumn.One });
            }
            else if (msg.type === 'openFile') {
                // Open an imported file by module name
                let filePath = null;

                // msg.name is the module name (e.g. "Compiler.Frontend.Lexer.CLexerMain")
                // msg.file may be set but is often undefined — resolve from name
                const moduleName = msg.name || msg.file;
                if (moduleName) {
                    filePath = resolveAilangModule(moduleName, e.document);
                }

                if (filePath && fs.existsSync(filePath)) {
                    vscode.workspace.openTextDocument(filePath).then(doc => {
                        vscode.window.showTextDocument(doc, vscode.ViewColumn.One);
                    });
                } else {
                    vscode.window.showWarningMessage('Could not find file for: ' + (moduleName || '(unknown)'));
                }
            }
        });

        // Auto-refresh on save
        const saveSub = vscode.workspace.onDidSaveTextDocument(doc => {
            if (doc.uri.toString() === e.document.uri.toString()) {
                updateGraph();
            }
        });

        // Auto-refresh on text change (debounced 1.5s so we're not hammering WSL)
        const changeSub = vscode.workspace.onDidChangeTextDocument(ev => {
            if (ev.document.uri.toString() === e.document.uri.toString()) {
                if (refreshTimer) clearTimeout(refreshTimer);
                refreshTimer = setTimeout(updateGraph, 1500);
            }
        });

        panel.onDidDispose(() => {
            saveSub.dispose();
            changeSub.dispose();
            if (refreshTimer) clearTimeout(refreshTimer);
        });
    }));

    // ─── Manuals Sidebar ─────────────────────────────────────────────
    vscode.window.registerTreeDataProvider('ailangManuals', new ManualsProvider(__dirname));

    // ─── Document Symbol Provider (Outline) ──────────────────────────
    context.subscriptions.push(vscode.languages.registerDocumentSymbolProvider('ailang', {
        provideDocumentSymbols(doc) {
            return new Promise(resolve => {
                runTool(doc, (err, json) => {
                    if (err || !json || !json.symbols) { resolve([]); return; }

                    // Build hierarchical symbols: top-level defs contain their children
                    const topLevel = [];
                    const scopeMap = {};

                    // First pass: create all top-level symbols (no scope or scope is null)
                    json.symbols.forEach(sym => {
                        const kind = mapSymbolKind(sym.kind);
                        const line = Math.max(0, sym.line - 1);
                        const r = new vscode.Range(line, 0, line, 200);
                        const ds = new vscode.DocumentSymbol(sym.name, sym.kind, kind, r, r);
                        ds.children = [];

                        if (!sym.scope) {
                            topLevel.push(ds);
                            scopeMap[sym.name] = ds;
                        } else {
                            // Child — attach to parent if exists
                            const parent = scopeMap[sym.scope];
                            if (parent) {
                                parent.children.push(ds);
                            } else {
                                topLevel.push(ds);
                            }
                        }
                    });
                    resolve(topLevel);
                });
            });
        }
    }));

    // ─── Hover Provider (enhanced with scope + params) ───────────────
    context.subscriptions.push(vscode.languages.registerHoverProvider('ailang', {
        provideHover(doc, pos) {
            const range = doc.getWordRangeAtPosition(pos);
            if (!range) return null;
            const word = doc.getText(range);
            const data = symbolCache.get(doc.uri.toString());
            if (!data || !data.symbols) return null;

            // Find all matching symbols
            const matches = data.symbols.filter(s => s.name === word);
            if (matches.length === 0) {
                // Check if it's a builtin
                if (BUILTINS.includes(word)) {
                    return new vscode.Hover(`**Builtin** \`${word}\``);
                }
                if (KEYWORDS.includes(word)) {
                    return new vscode.Hover(`**Keyword** \`${word}\``);
                }
                return null;
            }

            const parts = matches.map(sym => {
                let info = `**${sym.kind}** \`${sym.name}\``;
                if (sym.scope) info += `\n\nScope: \`${sym.scope}\``;
                info += `\n\nLine ${sym.line}`;

                // Show params if this is a function
                if (sym.kind === 'Function' || sym.kind === 'SubRoutine' || sym.kind === 'Combinator') {
                    const params = data.symbols.filter(s =>
                        s.kind === 'Parameter' && s.scope === sym.name
                    );
                    const output = data.symbols.find(s =>
                        s.kind === 'Output' && s.scope === sym.name
                    );
                    if (params.length > 0) {
                        info += '\n\n**Params:** ' + params.map(p => `\`${p.name}\``).join(', ');
                    }
                    if (output) {
                        info += `\n\n**Returns:** \`${output.name}\``;
                    }

                    // Show callers
                    if (data.calls) {
                        const callers = [...new Set(
                            data.calls.filter(c => c.to === sym.name).map(c => c.from)
                        )];
                        if (callers.length > 0) {
                            info += '\n\n**Called by:** ' + callers.map(c => `\`${c}\``).join(', ');
                        }
                    }
                }

                // Show fields if this is a pool
                if (sym.kind.endsWith('Pool')) {
                    const fields = data.symbols.filter(s =>
                        s.kind === 'Field' && s.scope === sym.name
                    );
                    if (fields.length > 0) {
                        info += '\n\n**Fields:** ' + fields.map(f => `\`${f.name}\``).join(', ');
                    }
                }

                return info;
            });

            return new vscode.Hover(new vscode.MarkdownString(parts.join('\n\n---\n\n')));
        }
    }));

    // ─── Go-to-Definition ────────────────────────────────────────────
    context.subscriptions.push(vscode.languages.registerDefinitionProvider('ailang', {
        provideDefinition(doc, pos) {
            const range = doc.getWordRangeAtPosition(pos);
            if (!range) return null;
            const word = doc.getText(range);
            const data = symbolCache.get(doc.uri.toString());
            if (!data || !data.symbols) return null;

            // Find defining symbol (prefer non-Parameter, non-Field definitions)
            const defKinds = ['Function', 'SubRoutine', 'Combinator', 'FixedPool',
                'DynamicPool', 'LinkagePool', 'TemporalPool', 'NeuralPool',
                'KernelPool', 'ActorPool', 'SecurityPool', 'ConstrainedPool',
                'FilePool', 'SubPool', 'LoopMain', 'LoopActor', 'LoopStart',
                'Macro', 'Variable', 'Module', 'Export'];

            let sym = data.symbols.find(s => s.name === word && defKinds.includes(s.kind));
            if (!sym) sym = data.symbols.find(s => s.name === word);
            if (!sym) return null;

            const line = Math.max(0, sym.line - 1);
            return new vscode.Location(doc.uri, new vscode.Position(line, 0));
        }
    }));

    // ─── Completion Provider ─────────────────────────────────────────
    context.subscriptions.push(vscode.languages.registerCompletionItemProvider('ailang', {
        provideCompletionItems(doc, pos) {
            const items = [];
            const lineText = doc.lineAt(pos).text;
            const textBefore = lineText.substring(0, pos.character);

            // --- Check if we just typed "Keyword." for scaffolding ---
            const dotMatch = textBefore.match(/(\w+)\.$/);
            if (dotMatch) {
                const kw = dotMatch[1];
                // Check canonical name
                let scaffoldKey = kw;
                // Also check if they typed a shorthand before the dot
                if (ALIASES[kw.toUpperCase()]) scaffoldKey = ALIASES[kw.toUpperCase()];

                if (SCAFFOLDS[scaffoldKey]) {
                    const sc = SCAFFOLDS[scaffoldKey];
                    const ci = new vscode.CompletionItem(sc.label, vscode.CompletionItemKind.Snippet);
                    ci.detail = sc.detail;
                    ci.insertText = new vscode.SnippetString(sc.snippet);
                    // Replace the "Keyword." prefix we already typed
                    const startCol = pos.character - dotMatch[0].length;
                    ci.range = new vscode.Range(pos.line, startCol, pos.line, pos.character);
                    ci.sortText = '!0_' + sc.label; // Sort first
                    ci.preselect = true;
                    items.push(ci);
                    return items; // Return scaffold only — don't clutter with other completions
                }
            }

            // --- Shorthand alias completions ---
            const wordMatch = textBefore.match(/(\w+)$/);
            const typedWord = wordMatch ? wordMatch[1] : '';
            const typedUpper = typedWord.toUpperCase();

            if (typedWord.length >= 2) {
                Object.entries(ALIASES).forEach(([short, canon]) => {
                    if (short.startsWith(typedUpper) || short === typedUpper) {
                        const ci = new vscode.CompletionItem(short + ' \u2192 ' + canon, vscode.CompletionItemKind.Snippet);
                        ci.insertText = canon;
                        ci.detail = 'Shorthand alias';
                        ci.filterText = short + ' ' + canon + ' ' + typedWord;
                        ci.sortText = '!1_' + short;
                        // Replace the typed shorthand
                        if (wordMatch) {
                            const startCol = pos.character - typedWord.length;
                            ci.range = new vscode.Range(pos.line, startCol, pos.line, pos.character);
                        }
                        items.push(ci);
                    }
                });
            }

            // --- Keywords (with shorthand hints) ---
            KEYWORDS.forEach(kw => {
                const i = new vscode.CompletionItem(kw, vscode.CompletionItemKind.Keyword);
                const shorts = REVERSE_ALIASES[kw];
                if (shorts) {
                    i.detail = 'Shorthand: ' + shorts.join(', ');
                    i.filterText = kw + ' ' + shorts.join(' ');
                }
                i.sortText = '2_' + kw;
                items.push(i);
            });

            // --- Builtins (with shorthand hints) ---
            BUILTINS.forEach(bi => {
                const i = new vscode.CompletionItem(bi, vscode.CompletionItemKind.Function);
                const shorts = REVERSE_ALIASES[bi];
                i.detail = shorts ? 'AILang builtin \u00B7 ' + shorts.join(', ') : 'AILang builtin';
                if (shorts) i.filterText = bi + ' ' + shorts.join(' ');
                i.sortText = '1_' + bi;
                items.push(i);
            });

            // Symbols from current file
            const data = symbolCache.get(doc.uri.toString());
            if (data && data.symbols) {
                const seen = new Set();
                data.symbols.forEach(sym => {
                    if (seen.has(sym.name)) return;
                    seen.add(sym.name);

                    let ck;
                    switch (sym.kind) {
                        case 'Function': case 'SubRoutine': case 'Combinator':
                            ck = vscode.CompletionItemKind.Function; break;
                        case 'Parameter': case 'Variable':
                            ck = vscode.CompletionItemKind.Variable; break;
                        case 'Field':
                            ck = vscode.CompletionItemKind.Field; break;
                        case 'Import': case 'Module':
                            ck = vscode.CompletionItemKind.Module; break;
                        default:
                            if (sym.kind.endsWith('Pool')) ck = vscode.CompletionItemKind.Struct;
                            else ck = vscode.CompletionItemKind.Text;
                    }
                    const ci = new vscode.CompletionItem(sym.name, ck);
                    ci.detail = sym.kind + (sym.scope ? ` (in ${sym.scope})` : '');
                    ci.sortText = '0_' + sym.name; // File symbols sort first
                    items.push(ci);
                });
            }

            return items;
        }
    }, '.', '@')); // Trigger on . and @ for pool.member and ptr@field

    // ─── Code Lens (Run button above Main) ───────────────────────────
    context.subscriptions.push(vscode.languages.registerCodeLensProvider('ailang', {
        provideCodeLenses(doc) {
            const text = doc.getText();
            const regex = /SubRoutine\.\w+Main\w*/g;
            const lenses = [];
            let m;
            while ((m = regex.exec(text)) !== null) {
                const pos = doc.positionAt(m.index);
                const r = new vscode.Range(pos, pos);
                lenses.push(new vscode.CodeLens(r, { title: '$(play) Run', command: 'ailang.run' }));
            }
            return lenses;
        }
    }));

    // ─── Format-on-Save: Expand Shorthands ───────────────────────────
    context.subscriptions.push(vscode.workspace.onWillSaveTextDocument(ev => {
        if (ev.document.languageId !== 'ailang') return;

        const edits = [];
        const text = ev.document.getText();

        // Build a regex matching all alias keys as whole words (case-insensitive input)
        const aliasKeys = Object.keys(ALIASES);
        // Sort longest first so "FLP" matches before "FL"
        aliasKeys.sort((a, b) => b.length - a.length);
        const pattern = new RegExp('\\b(' + aliasKeys.join('|') + ')\\b', 'g');

        let match;
        while ((match = pattern.exec(text)) !== null) {
            const shorthand = match[1];
            const canon = ALIASES[shorthand] || ALIASES[shorthand.toUpperCase()];
            if (!canon) continue;

            // Don't expand inside strings or comments
            const lineNum = ev.document.positionAt(match.index).line;
            const lineText = ev.document.lineAt(lineNum).text;
            const colStart = ev.document.positionAt(match.index).character;

            // Simple string/comment check: skip if inside quotes or after //
            const beforeMatch = lineText.substring(0, colStart);
            const quoteCount = (beforeMatch.match(/"/g) || []).length;
            if (quoteCount % 2 !== 0) continue; // inside a string
            if (beforeMatch.includes('//')) continue; // inside a comment

            const startPos = ev.document.positionAt(match.index);
            const endPos = ev.document.positionAt(match.index + shorthand.length);
            edits.push(vscode.TextEdit.replace(new vscode.Range(startPos, endPos), canon));
        }

        if (edits.length > 0) {
            ev.waitUntil(Promise.resolve(edits));
        }
    }));
}

// =============================================================================
// LSP RUNNER
// =============================================================================

function runLsp(document) {
    runTool(document, (err, json) => {
        if (!json) return;

        const diagsByFile = new Map();

        if (json.diagnostics) {
            json.diagnostics.forEach(d => {
                const line = Math.max(0, (d.line || 1) - 1);
                const col = Math.max(0, (d.col || 0));
                const r = new vscode.Range(line, col, line, col + 200);

                let sev;
                switch (d.severity) {
                    case 'Error':   sev = vscode.DiagnosticSeverity.Error; break;
                    case 'Warning': sev = vscode.DiagnosticSeverity.Warning; break;
                    case 'Hint':    sev = vscode.DiagnosticSeverity.Hint; break;
                    default:        sev = vscode.DiagnosticSeverity.Information; break;
                }

                const diag = new vscode.Diagnostic(r, d.message, sev);
                diag.source = d.source || 'ailang';

                // Route to correct file
                let fileUri = document.uri.toString();
                if (d.file && d.file !== '' && d.file !== 'main') {
                    const resolved = resolveAilangFile(d.file, document);
                    if (resolved) fileUri = resolved;
                }

                if (!diagsByFile.has(fileUri)) diagsByFile.set(fileUri, []);
                diagsByFile.get(fileUri).push(diag);
            });
        }

        // Clear old diagnostics, then set new ones per file
        diagnosticCollection.clear();
        diagsByFile.forEach((diags, uri) => {
            diagnosticCollection.set(vscode.Uri.parse(uri), diags);
        });

        if (json) symbolCache.set(document.uri.toString(), json);
    });
}

function resolveAilangFile(fileRef, document) {
    const docDir = path.dirname(document.fileName);

    // WSL absolute path
    if (fileRef.startsWith('/mnt/')) {
        const winPath = fileRef
            .replace(/^\/mnt\/([a-z])\//, (_, l) => l.toUpperCase() + ':\\')
            .replace(/\//g, '\\');
        if (fs.existsSync(winPath)) return vscode.Uri.file(winPath).toString();
    }

    // Module name like "Library.XArrays" or "Compiler.Frontend.Lexer.CLexerMain"
    const candidates = [
        path.join(docDir, fileRef + '.ailang'),
        path.join(docDir, fileRef.replace(/\./g, '/') + '.ailang'),
        path.join(docDir, 'Librarys', fileRef + '.ailang'),
        path.join(docDir, 'Librarys', fileRef.replace(/\./g, '/') + '.ailang'),
        path.join(docDir, 'Librarys', 'Library.' + fileRef + '.ailang'),
    ];

    for (const c of candidates) {
        if (fs.existsSync(c)) return vscode.Uri.file(c).toString();
    }
    return null;
}

function runTool(document, callback) {
    const config = vscode.workspace.getConfiguration('ailang');
    let lspPath = config.get('lspPath');

    let lspBin;
    if (lspPath) {
        lspBin = lspPath;
        if (lspBin.startsWith('./')) {
            // Resolve relative to workspace folder first, then document dir as fallback
            if (vscode.workspace.workspaceFolders) {
                lspBin = path.join(vscode.workspace.workspaceFolders[0].uri.fsPath, lspBin);
            } else {
                lspBin = path.join(path.dirname(document.fileName), lspBin);
            }
        }
    } else {
        // No config set — try next to the document, then fall back to extension dir
        const docDirBin = path.join(path.dirname(document.fileName), 'ailang_lsp.x');
        if (fs.existsSync(docDirBin)) {
            lspBin = docDirBin;
        } else {
            lspBin = path.join(__dirname, 'ailang_lsp.x');
        }
    }

    // Convert paths for WSL on Windows
    const cmd = toWslPath(lspBin);
    const filePath = toWslPath(document.fileName);
    const fullCmd = `chmod +x "${cmd}" 2>/dev/null; "${cmd}" "${filePath}"`;

    wslExec(fullCmd, (err, stdout, stderr) => {
        // Try to parse JSON from stdout FIRST, even if exit code was non-zero.
        // The LSP may produce valid JSON then hit an error in a later phase.
        let json = null;
        if (stdout) {
            const lines = stdout.split('\n');
            for (const line of lines) {
                const trimmed = line.trim();
                if (trimmed.startsWith('{')) {
                    try { json = JSON.parse(trimmed); break; } catch (_) {}
                }
            }
        }

        // If we got valid JSON, use it regardless of exit code
        if (json) {
            callback(null, json);
            return;
        }

        // Only truly fail if there's no usable data
        if (err) {
            console.error('LSP Error:', stderr);
            callback(err, null);
            return;
        }

        callback(null, null);
    });
}

// =============================================================================
// REPLACEMENT: getFlowHTML → getConnectomeHTML
// =============================================================================
function getConnectomeHTML(data, fileUri) {
    const nodes = [];
    const edges = [];
    const groups = {};

    const poolKinds = ['FixedPool','DynamicPool','TemporalPool','NeuralPool',
        'KernelPool','ActorPool','SecurityPool','ConstrainedPool','FilePool',
        'LinkagePool','SubPool'];

    const colorMap = {
        'Import':     '#e94560',
        'Pool':       '#0f8bff',
        'Function':   '#a855f7',
        'Combinator': '#a855f7',
        'SubRoutine': '#f97316',
        'Loop':       '#16a085',
        'Field':      '#6b7280',
        'Variable':   '#6b7280',
        'Parameter':  '#6b7280',
        'Export':     '#eab308',
        'Module':     '#e94560',
        'Macro':      '#ec4899',
        'AcronymDefs':'#6b7280',
        'Lambda':     '#a855f7',
    };

    if (data && data.symbols) {
        data.symbols.forEach((s, i) => {
            let group, color;
            if (s.kind === 'Import') {
                group = 'Imports'; color = colorMap['Import'];
            } else if (poolKinds.includes(s.kind)) {
                group = 'Pools'; color = colorMap['Pool'];
            } else if (s.kind === 'Function' || s.kind === 'Combinator' || s.kind === 'Lambda') {
                group = 'Functions'; color = colorMap['Function'];
            } else if (s.kind === 'SubRoutine') {
                group = 'SubRoutines'; color = colorMap['SubRoutine'];
            } else if (s.kind.startsWith('Loop')) {
                group = 'Loops'; color = colorMap['Loop'];
            } else if (s.kind === 'Export') {
                group = 'Exports'; color = colorMap['Export'];
            } else if (s.kind === 'Macro') {
                group = 'Macros'; color = colorMap['Macro'];
            } else if (s.kind === 'Field' && s.scope) {
                group = 'Fields'; color = colorMap['Field'];
            } else {
                return; // skip params, variables for top-level
            }

            nodes.push({
                id: s.name,
                label: s.name,
                kind: s.kind,
                group,
                color,
                line: s.line || 0,
                scope: s.scope || null
            });
        });

        if (data.calls) {
            const nodeIds = new Set(nodes.map(n => n.id));
            const seen = new Set();
            data.calls.forEach(c => {
                const key = `${c.from}->${c.to}`;
                if (!seen.has(key) && nodeIds.has(c.from) && nodeIds.has(c.to)) {
                    seen.add(key);
                    edges.push({ from: c.from, to: c.to });
                }
            });
        }

        // Add scope edges (field -> parent pool/function)
        nodes.forEach(n => {
            if (n.scope) {
                const parent = nodes.find(p => p.id === n.scope);
                if (parent) {
                    const key = `${n.scope}->>${n.id}`;
                    edges.push({ from: n.scope, to: n.id, type: 'scope' });
                }
            }
        });
    }

    // Add import file paths for navigation
    const imports = [];
    if (data && data.imports) {
        data.imports.forEach(imp => {
            imports.push({ name: imp.name, file: imp.file || null, line: imp.line || 0 });
        });
    }

    const graphData = JSON.stringify({ nodes, edges, imports });

    return `<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta http-equiv="Content-Security-Policy"
      content="default-src 'none'; style-src 'unsafe-inline'; script-src 'unsafe-inline';">
<style>
* { margin:0; padding:0; box-sizing:border-box; }
body { background:#111118; overflow:hidden; font-family:'Segoe UI',system-ui,sans-serif; }
canvas { display:block; cursor:grab; }
canvas.dragging { cursor:grabbing; }

#hud {
    position:fixed; top:8px; left:8px; right:8px;
    display:flex; gap:8px; align-items:center; z-index:10; pointer-events:none;
}
#hud > * { pointer-events:auto; }
#search {
    background:#1e1e2e; border:1px solid #333; border-radius:4px;
    color:#d4d4d4; padding:5px 10px; font-size:12px; width:200px; outline:none;
}
#search:focus { border-color:#a855f7; }
.filter-btn {
    background:#1e1e2e; border:1px solid #333; border-radius:4px;
    color:#888; padding:4px 8px; font-size:11px; cursor:pointer; transition:all 0.15s;
}
.filter-btn:hover { border-color:#555; color:#ccc; }
.filter-btn.active { border-color:var(--fc); color:var(--fc); background:rgba(255,255,255,0.05); }
#stats {
    margin-left:auto; color:#444; font-size:10px; letter-spacing:0.5px;
}

#tooltip {
    display:none; position:fixed; background:#1e1e2e; border:1px solid #444;
    border-radius:6px; padding:10px 14px; color:#d4d4d4; font-size:12px;
    z-index:20; pointer-events:none; max-width:300px; box-shadow:0 4px 20px rgba(0,0,0,0.5);
}
#tooltip .tt-kind { font-size:10px; text-transform:uppercase; letter-spacing:1px; margin-bottom:4px; }
#tooltip .tt-name { font-size:14px; font-weight:600; margin-bottom:6px; }
#tooltip .tt-detail { color:#888; font-size:11px; }
#tooltip .tt-hint { color:#555; font-size:10px; margin-top:6px; border-top:1px solid #2a2a2a; padding-top:6px; }

#detail-panel {
    display:none; position:fixed; right:0; top:0; bottom:0; width:280px;
    background:#161622; border-left:1px solid #2a2a2a; z-index:15;
    padding:16px; overflow-y:auto; color:#d4d4d4;
}
#detail-panel .dp-close {
    position:absolute; top:8px; right:12px; cursor:pointer; color:#666;
    font-size:18px; line-height:1;
}
#detail-panel .dp-close:hover { color:#fff; }
#detail-panel .dp-kind { font-size:10px; text-transform:uppercase; letter-spacing:1px; margin-bottom:4px; }
#detail-panel .dp-name { font-size:18px; font-weight:700; margin-bottom:4px; }
#detail-panel .dp-scope { font-size:12px; color:#888; margin-bottom:12px; }
#detail-panel .dp-section { margin-bottom:12px; }
#detail-panel .dp-section-title {
    font-size:10px; text-transform:uppercase; letter-spacing:1px;
    color:#666; margin-bottom:6px;
}
#detail-panel .dp-link {
    display:block; padding:4px 8px; margin:2px 0; border-radius:3px;
    color:#a855f7; font-size:12px; cursor:pointer; text-decoration:none;
    transition:background 0.1s;
}
#detail-panel .dp-link:hover { background:rgba(168,85,247,0.1); }
#detail-panel .dp-goto {
    display:inline-block; margin-top:8px; padding:6px 14px;
    background:#a855f7; color:#fff; border:none; border-radius:4px;
    font-size:12px; cursor:pointer; transition:opacity 0.15s;
}
#detail-panel .dp-goto:hover { opacity:0.85; }

#legend {
    position:fixed; bottom:8px; left:8px; display:flex; gap:10px;
    font-size:10px; color:#555; z-index:10;
}
.legend-item { display:flex; align-items:center; gap:4px; }
.legend-dot { width:8px; height:8px; border-radius:50%; }
</style>
</head>
<body>
<div id="hud">
    <input id="search" type="text" placeholder="Search symbols..." autocomplete="off">
    <button class="filter-btn active" data-group="all" style="--fc:#fff">All</button>
    <button class="filter-btn active" data-group="Imports" style="--fc:#e94560">Imports</button>
    <button class="filter-btn active" data-group="Pools" style="--fc:#0f8bff">Pools</button>
    <button class="filter-btn active" data-group="Functions" style="--fc:#a855f7">Functions</button>
    <button class="filter-btn active" data-group="SubRoutines" style="--fc:#f97316">SubRoutines</button>
    <button class="filter-btn active" data-group="Loops" style="--fc:#16a085">Loops</button>
    <span id="stats"></span>
</div>
<div id="tooltip"><div class="tt-kind"></div><div class="tt-name"></div><div class="tt-detail"></div><div class="tt-hint"></div></div>
<div id="detail-panel">
    <span class="dp-close">&times;</span>
    <div class="dp-kind"></div>
    <div class="dp-name"></div>
    <div class="dp-scope"></div>
    <div id="dp-calls-out" class="dp-section"></div>
    <div id="dp-calls-in" class="dp-section"></div>
    <div id="dp-children" class="dp-section"></div>
    <button class="dp-goto" id="dp-goto">Go to Definition</button>
    <button class="dp-goto" id="dp-open-file" style="display:none;background:#e94560;margin-left:4px;">Open File</button>
</div>
<div id="legend">
    <div class="legend-item"><div class="legend-dot" style="background:#e94560"></div>Import</div>
    <div class="legend-item"><div class="legend-dot" style="background:#0f8bff"></div>Pool</div>
    <div class="legend-item"><div class="legend-dot" style="background:#a855f7"></div>Function</div>
    <div class="legend-item"><div class="legend-dot" style="background:#f97316"></div>SubRoutine</div>
    <div class="legend-item"><div class="legend-dot" style="background:#16a085"></div>Loop</div>
</div>
<canvas id="c"></canvas>

<script>
(function(){
const vscode = acquireVsCodeApi();
const data = ${graphData};
const canvas = document.getElementById('c');
const ctx = canvas.getContext('2d');
const tooltip = document.getElementById('tooltip');
const detail = document.getElementById('detail-panel');
const searchInput = document.getElementById('search');
const statsEl = document.getElementById('stats');

let W, H, dpr;
function resize() {
    dpr = window.devicePixelRatio || 1;
    W = window.innerWidth; H = window.innerHeight;
    canvas.width = W * dpr; canvas.height = H * dpr;
    canvas.style.width = W + 'px'; canvas.style.height = H + 'px';
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
}
resize();
window.addEventListener('resize', () => { resize(); draw(); });

// --- Physics layout ---
const nodes = data.nodes.map((n, i) => {
    const angle = (i / data.nodes.length) * Math.PI * 2;
    const r = 120 + Math.random() * 80;
    return {
        ...n,
        x: W/2 + Math.cos(angle) * r,
        y: H/2 + Math.sin(angle) * r,
        vx: 0, vy: 0,
        radius: n.group === 'Fields' ? 6 : (n.kind === 'SubRoutine' ? 14 : 10),
        visible: true,
        matched: true
    };
});
const nodeMap = {};
nodes.forEach(n => nodeMap[n.id] = n);

const edges = data.edges.map(e => ({
    source: nodeMap[e.from],
    target: nodeMap[e.to],
    type: e.type || 'call'
})).filter(e => e.source && e.target);

// Group filters
const activeGroups = new Set(['Imports','Pools','Functions','SubRoutines','Loops','Fields','Exports','Macros']);
document.querySelectorAll('.filter-btn').forEach(btn => {
    btn.addEventListener('click', () => {
        const g = btn.dataset.group;
        if (g === 'all') {
            const allActive = document.querySelectorAll('.filter-btn.active').length ===
                              document.querySelectorAll('.filter-btn').length;
            document.querySelectorAll('.filter-btn').forEach(b => {
                if (allActive) { b.classList.remove('active'); activeGroups.clear(); }
                else { b.classList.add('active'); if(b.dataset.group!=='all') activeGroups.add(b.dataset.group); }
            });
        } else {
            btn.classList.toggle('active');
            if (activeGroups.has(g)) activeGroups.delete(g); else activeGroups.add(g);
        }
        updateVisibility();
    });
});

// Search
searchInput.addEventListener('input', () => updateVisibility());

function updateVisibility() {
    const q = searchInput.value.toLowerCase().trim();
    nodes.forEach(n => {
        n.matched = !q || n.id.toLowerCase().includes(q) || n.kind.toLowerCase().includes(q);
        n.visible = activeGroups.has(n.group) && n.matched;
    });
}

// Camera
let camX = 0, camY = 0, camZoom = 1;
let dragStart = null, dragCam = null, dragNode = null;
let hoveredNode = null, selectedNode = null;

function screenToWorld(sx, sy) {
    return { x: (sx - W/2) / camZoom + W/2 - camX, y: (sy - H/2) / camZoom + H/2 - camY };
}

function worldToScreen(wx, wy) {
    return { x: (wx - W/2 + camX) * camZoom + W/2, y: (wy - H/2 + camY) * camZoom + H/2 };
}

function hitTest(mx, my) {
    const p = screenToWorld(mx, my);
    for (let i = nodes.length - 1; i >= 0; i--) {
        const n = nodes[i];
        if (!n.visible) continue;
        const dx = p.x - n.x, dy = p.y - n.y;
        if (dx*dx + dy*dy < (n.radius + 4) * (n.radius + 4)) return n;
    }
    return null;
}

canvas.addEventListener('mousedown', e => {
    const n = hitTest(e.clientX, e.clientY);
    if (n) {
        dragNode = n;
        canvas.classList.add('dragging');
    } else {
        dragStart = { x: e.clientX, y: e.clientY };
        dragCam = { x: camX, y: camY };
        canvas.classList.add('dragging');
    }
});

canvas.addEventListener('mousemove', e => {
    if (dragNode) {
        const p = screenToWorld(e.clientX, e.clientY);
        dragNode.x = p.x; dragNode.y = p.y;
        dragNode.vx = 0; dragNode.vy = 0;
    } else if (dragStart) {
        camX = dragCam.x + (e.clientX - dragStart.x) / camZoom;
        camY = dragCam.y + (e.clientY - dragStart.y) / camZoom;
    } else {
        const n = hitTest(e.clientX, e.clientY);
        hoveredNode = n;
        if (n) {
            canvas.style.cursor = 'pointer';
            showTooltip(n, e.clientX, e.clientY);
        } else {
            canvas.style.cursor = 'grab';
            tooltip.style.display = 'none';
        }
    }
});

canvas.addEventListener('mouseup', () => {
    if (dragNode && !dragStart) {
        // Was a click on a node, not a drag
    }
    dragNode = null; dragStart = null; dragCam = null;
    canvas.classList.remove('dragging');
});

canvas.addEventListener('click', e => {
    const n = hitTest(e.clientX, e.clientY);
    if (n) {
        selectedNode = n;
        showDetail(n);
    }
});

canvas.addEventListener('dblclick', e => {
    const n = hitTest(e.clientX, e.clientY);
    if (n) {
        // Double-click: go to definition
        vscode.postMessage({ type: 'goto', line: n.line, id: n.id });
    }
});

canvas.addEventListener('wheel', e => {
    e.preventDefault();
    const factor = e.deltaY > 0 ? 0.92 : 1.08;
    camZoom = Math.max(0.15, Math.min(5, camZoom * factor));
}, { passive: false });

function showTooltip(n, mx, my) {
    tooltip.querySelector('.tt-kind').textContent = n.kind;
    tooltip.querySelector('.tt-kind').style.color = n.color;
    tooltip.querySelector('.tt-name').textContent = n.id;

    const callsOut = edges.filter(e => e.source.id === n.id && e.type === 'call').map(e => e.target.id);
    const callsIn = edges.filter(e => e.target.id === n.id && e.type === 'call').map(e => e.source.id);
    let detail = '';
    if (callsOut.length) detail += 'Calls: ' + callsOut.join(', ') + '\\n';
    if (callsIn.length) detail += 'Called by: ' + callsIn.join(', ');
    if (n.scope) detail += (detail ? '\\n' : '') + 'Scope: ' + n.scope;
    tooltip.querySelector('.tt-detail').textContent = detail || n.group;

    tooltip.querySelector('.tt-hint').textContent = 'Click for details \u00B7 Double-click to go to definition';
    tooltip.style.display = 'block';
    tooltip.style.left = Math.min(mx + 12, W - 310) + 'px';
    tooltip.style.top = Math.min(my + 12, H - 120) + 'px';
}

function showDetail(n) {
    detail.style.display = 'block';
    detail.querySelector('.dp-kind').textContent = n.kind;
    detail.querySelector('.dp-kind').style.color = n.color;
    detail.querySelector('.dp-name').textContent = n.id;
    detail.querySelector('.dp-scope').textContent = n.scope ? 'in ' + n.scope : '';

    // Calls out
    const outSec = document.getElementById('dp-calls-out');
    const callsOut = edges.filter(e => e.source.id === n.id && e.type === 'call');
    if (callsOut.length) {
        outSec.innerHTML = '<div class="dp-section-title">Calls (' + callsOut.length + ')</div>';
        callsOut.forEach(e => {
            const a = document.createElement('a');
            a.className = 'dp-link';
            a.textContent = '\u2192 ' + e.target.id;
            a.addEventListener('click', () => focusNode(e.target));
            outSec.appendChild(a);
        });
    } else { outSec.innerHTML = ''; }

    // Calls in
    const inSec = document.getElementById('dp-calls-in');
    const callsIn = edges.filter(e => e.target.id === n.id && e.type === 'call');
    if (callsIn.length) {
        inSec.innerHTML = '<div class="dp-section-title">Called by (' + callsIn.length + ')</div>';
        callsIn.forEach(e => {
            const a = document.createElement('a');
            a.className = 'dp-link';
            a.textContent = '\u2190 ' + e.source.id;
            a.addEventListener('click', () => focusNode(e.source));
            inSec.appendChild(a);
        });
    } else { inSec.innerHTML = ''; }

    // Children (scope)
    const childSec = document.getElementById('dp-children');
    const children = nodes.filter(c => c.scope === n.id);
    if (children.length) {
        childSec.innerHTML = '<div class="dp-section-title">Contains (' + children.length + ')</div>';
        children.forEach(c => {
            const a = document.createElement('a');
            a.className = 'dp-link';
            a.textContent = c.kind + ': ' + c.id;
            a.addEventListener('click', () => focusNode(c));
            childSec.appendChild(a);
        });
    } else { childSec.innerHTML = ''; }

    // Go to definition button
    document.getElementById('dp-goto').onclick = () => {
        vscode.postMessage({ type: 'goto', line: n.line, id: n.id });
    };

    // Open file button (for imports)
    const openBtn = document.getElementById('dp-open-file');
    const imp = data.imports.find(i => i.name === n.id);
    if (n.kind === 'Import' && imp) {
        openBtn.style.display = 'inline-block';
        openBtn.onclick = () => {
            vscode.postMessage({ type: 'openFile', file: imp.file, name: n.id });
        };
    } else {
        openBtn.style.display = 'none';
    }
}

function focusNode(n) {
    selectedNode = n;
    showDetail(n);
    // Animate camera to center on node
    camX = -(n.x - W/2);
    camY = -(n.y - H/2);
    camZoom = 1.5;
}

detail.querySelector('.dp-close').addEventListener('click', () => {
    detail.style.display = 'none';
    selectedNode = null;
});

// --- Physics simulation ---
let simRunning = true;
let simCooldown = 300; // frames of simulation

function simulate() {
    const alpha = Math.max(0.001, simCooldown > 0 ? 0.3 * (simCooldown / 300) : 0.001);
    if (simCooldown > 0) simCooldown--;

    // Repulsion between all visible nodes
    for (let i = 0; i < nodes.length; i++) {
        if (!nodes[i].visible) continue;
        for (let j = i + 1; j < nodes.length; j++) {
            if (!nodes[j].visible) continue;
            const a = nodes[i], b = nodes[j];
            let dx = b.x - a.x, dy = b.y - a.y;
            let dist = Math.sqrt(dx*dx + dy*dy) || 1;
            const force = -800 / (dist * dist);
            const fx = (dx / dist) * force * alpha;
            const fy = (dy / dist) * force * alpha;
            a.vx -= fx; a.vy -= fy;
            b.vx += fx; b.vy += fy;
        }
    }

    // Attraction along edges
    edges.forEach(e => {
        if (!e.source.visible || !e.target.visible) return;
        const dx = e.target.x - e.source.x;
        const dy = e.target.y - e.source.y;
        const dist = Math.sqrt(dx*dx + dy*dy) || 1;
        const idealDist = e.type === 'scope' ? 50 : 100;
        const force = (dist - idealDist) * 0.005 * alpha;
        const fx = (dx / dist) * force;
        const fy = (dy / dist) * force;
        e.source.vx += fx; e.source.vy += fy;
        e.target.vx -= fx; e.target.vy -= fy;
    });

    // Center gravity
    nodes.forEach(n => {
        if (!n.visible) return;
        n.vx += (W/2 - n.x) * 0.0005 * alpha;
        n.vy += (H/2 - n.y) * 0.0005 * alpha;
    });

    // Group clustering — same group nodes attract slightly
    const groupCenters = {};
    nodes.forEach(n => {
        if (!n.visible) return;
        if (!groupCenters[n.group]) groupCenters[n.group] = { x:0, y:0, count:0 };
        groupCenters[n.group].x += n.x;
        groupCenters[n.group].y += n.y;
        groupCenters[n.group].count++;
    });
    Object.keys(groupCenters).forEach(g => {
        const gc = groupCenters[g];
        gc.x /= gc.count; gc.y /= gc.count;
    });
    nodes.forEach(n => {
        if (!n.visible || !groupCenters[n.group]) return;
        const gc = groupCenters[n.group];
        n.vx += (gc.x - n.x) * 0.003 * alpha;
        n.vy += (gc.y - n.y) * 0.003 * alpha;
    });

    // Apply velocity with damping
    nodes.forEach(n => {
        if (dragNode === n) return;
        n.vx *= 0.85; n.vy *= 0.85;
        n.x += n.vx; n.y += n.vy;
    });
}

// --- Drawing ---
function draw() {
    ctx.clearRect(0, 0, W, H);
    ctx.save();
    ctx.translate(W/2, H/2);
    ctx.scale(camZoom, camZoom);
    ctx.translate(-W/2 + camX, -H/2 + camY);

    // Edges
    edges.forEach(e => {
        if (!e.source.visible || !e.target.visible) return;
        const isHighlighted = selectedNode &&
            (e.source.id === selectedNode.id || e.target.id === selectedNode.id);

        ctx.beginPath();
        ctx.moveTo(e.source.x, e.source.y);
        ctx.lineTo(e.target.x, e.target.y);

        if (e.type === 'scope') {
            ctx.strokeStyle = isHighlighted ? 'rgba(255,255,255,0.3)' : 'rgba(255,255,255,0.05)';
            ctx.setLineDash([3, 4]);
        } else {
            ctx.strokeStyle = isHighlighted ? 'rgba(168,85,247,0.7)' : 'rgba(255,255,255,0.08)';
            ctx.setLineDash([]);
        }
        ctx.lineWidth = isHighlighted ? 2 : 0.8;
        ctx.stroke();
        ctx.setLineDash([]);

        // Arrow head for call edges
        if (e.type !== 'scope') {
            const dx = e.target.x - e.source.x;
            const dy = e.target.y - e.source.y;
            const dist = Math.sqrt(dx*dx + dy*dy) || 1;
            const ux = dx/dist, uy = dy/dist;
            const ax = e.target.x - ux * (e.target.radius + 3);
            const ay = e.target.y - uy * (e.target.radius + 3);
            const sz = isHighlighted ? 6 : 4;
            ctx.beginPath();
            ctx.moveTo(ax, ay);
            ctx.lineTo(ax - ux*sz - uy*sz*0.5, ay - uy*sz + ux*sz*0.5);
            ctx.lineTo(ax - ux*sz + uy*sz*0.5, ay - uy*sz - ux*sz*0.5);
            ctx.closePath();
            ctx.fillStyle = ctx.strokeStyle;
            ctx.fill();
        }
    });

    // Nodes
    nodes.forEach(n => {
        if (!n.visible) return;
        const isSelected = selectedNode && selectedNode.id === n.id;
        const isConnected = selectedNode && edges.some(e =>
            (e.source.id === selectedNode.id && e.target.id === n.id) ||
            (e.target.id === selectedNode.id && e.source.id === n.id));
        const isHovered = hoveredNode && hoveredNode.id === n.id;

        const dimmed = selectedNode && !isSelected && !isConnected;
        const alpha = dimmed ? 0.2 : 1;

        // Glow for selected/hovered
        if (isSelected || isHovered) {
            ctx.beginPath();
            ctx.arc(n.x, n.y, n.radius + 8, 0, Math.PI * 2);
            ctx.fillStyle = n.color + '22';
            ctx.fill();
        }

        // Node circle
        ctx.beginPath();
        ctx.arc(n.x, n.y, n.radius, 0, Math.PI * 2);
        ctx.fillStyle = hexAlpha(n.color, alpha);
        ctx.fill();
        if (isSelected) {
            ctx.strokeStyle = '#fff';
            ctx.lineWidth = 2;
            ctx.stroke();
        }

        // Label
        const fontSize = n.radius > 10 ? 11 : 9;
        ctx.font = (isSelected ? 'bold ' : '') + fontSize + 'px "Segoe UI",system-ui,sans-serif';
        ctx.fillStyle = hexAlpha('#d4d4d4', dimmed ? 0.3 : 0.9);
        ctx.textAlign = 'center';
        ctx.fillText(n.label, n.x, n.y + n.radius + fontSize + 3);
    });

    ctx.restore();

    // Stats
    const vis = nodes.filter(n => n.visible).length;
    const visEdges = edges.filter(e => e.source.visible && e.target.visible).length;
    statsEl.textContent = vis + '/' + nodes.length + ' nodes \u00B7 ' + visEdges + ' edges';
}

function hexAlpha(hex, a) {
    const r = parseInt(hex.slice(1,3),16);
    const g = parseInt(hex.slice(3,5),16);
    const b = parseInt(hex.slice(5,7),16);
    return 'rgba(' + r + ',' + g + ',' + b + ',' + a + ')';
}

// --- Main loop ---
let dragNodeRef = null;
Object.defineProperty(window, '_dragNode', { get: () => dragNode });

function loop() {
    simulate();
    draw();
    requestAnimationFrame(loop);
}
loop();

// Reheat simulation on interaction
canvas.addEventListener('mousedown', () => { simCooldown = Math.max(simCooldown, 60); });
searchInput.addEventListener('input', () => { simCooldown = Math.max(simCooldown, 120); });
})();
</script>
</body>
</html>`;
}

// =============================================================================
// MANUALS SIDEBAR
// =============================================================================
class ManualsProvider {
    constructor(basePath) { this.basePath = basePath; }
    getTreeItem(el) { return el; }
    getChildren(el) {
        if (el || !this.basePath) return Promise.resolve([]);
        const docsPath = path.join(this.basePath, 'docs');
        if (!fs.existsSync(docsPath)) return Promise.resolve([]);
        return new Promise(resolve => {
            fs.readdir(docsPath, (err, files) => {
                if (err) { resolve([]); return; }
                resolve(files.filter(f => f.toLowerCase().endsWith('.md')).map(f =>
                    new ManualItem(f, vscode.TreeItemCollapsibleState.None, path.join(docsPath, f))
                ));
            });
        });
    }
}

class ManualItem extends vscode.TreeItem {
    constructor(label, state, filePath) {
        super(label, state);
        this.filePath = filePath;
        this.command = { command: 'markdown.showPreview', title: 'Open', arguments: [vscode.Uri.file(filePath)] };
        this.iconPath = new vscode.ThemeIcon('book');
    }
}

function deactivate() {}

module.exports = { activate, deactivate };