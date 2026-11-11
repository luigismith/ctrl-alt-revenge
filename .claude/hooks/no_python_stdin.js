// Blocca python che legge lo script da stdin (Bash e PowerShell).
// Su Windows la REPL di Python 3.13 senza console va in loop e riempie il disco:
// gli script si scrivono in un file e si lanciano con `python -I <file.py>`.
// Esce con 2 (blocco) e spiega su stderr; con 0 lascia passare.
'use strict';

let dati = '';
process.stdin.setEncoding('utf8');
process.stdin.on('data', (c) => { dati += c; });
process.stdin.on('end', () => {
  let cmd = '';
  try {
    const j = JSON.parse(dati || '{}');
    cmd = String((j.tool_input && j.tool_input.command) || '');
  } catch (e) {
    process.exit(0);
  }
  if (!cmd) process.exit(0);

  // Il testo che non è comando non conta: corpi delle here-string di PowerShell,
  // corpi degli heredoc e stringhe fra virgolette con spazi (messaggi, -c "...").
  cmd = cmd.replace(/@(['"])\r?\n[\s\S]*?\r?\n\1@/g, "@''@");
  cmd = cmd.replace(/<<(-?)[ \t]*(['"]?)([A-Za-z_][A-Za-z0-9_]*)\2([^\n]*)\n([\s\S]*?)(?:^|\n)[ \t]*\3[ \t]*(?=\n|$)/gm,
    (tutto, meno, q, nome, resto) => '<<' + meno + q + nome + q + resto + '\n' + nome);
  cmd = cmd.replace(/"(?:[^"\\]|\\.)*"|'[^']*'/g, (s) => (/\s/.test(s) ? s[0] + s[0] : s));

  // python, python3, python3.13, py (anche .exe e con percorso), in posizione di comando:
  // a inizio riga o dopo ; & | ( , con un & di PowerShell facoltativo.
  const tok = /(^|[;&|(\n])([ \t]*&?[ \t]*)(["']?)((?:[^\s;&|"'<>()]*[\\/])?)(python(?:3(?:\.\d+)?)?|py)(?:\.exe)?\3(?=[\s;&|<)]|$)/gim;
  const motivi = [];
  let m;
  while ((m = tok.exec(cmd)) !== null) {
    const fine = tok.lastIndex;
    const coda = cmd.slice(fine);
    const stop = coda.search(/[;&|\n]/);
    const args = (stop < 0 ? coda : coda.slice(0, stop)).trim();
    const prima = cmd.slice(0, m.index + m[1].length).replace(/\s+$/, '');

    const conScript =
      /\.pyw?\b/i.test(args) ||
      /(?:^|\s)-[A-Za-z]*[cm](?:\s|$)/.test(args) ||
      /(?:^|\s)(?:-V|--version|-h|--help)(?:\s|$)/.test(args);
    if (conScript) continue;

    const daPipe = /\|$/.test(prima) && !/\|\|$/.test(prima);
    const trattino = /(?:^|\s)-(?=\s|$|<)/.test(args);
    const redir = /</.test(args);
    const soloOpzioni = args === '' || args.split(/\s+/).every((a) => a.startsWith('-'));

    if (trattino) motivi.push('python con "-" legge lo script da stdin');
    else if (daPipe) motivi.push('pipe verso python senza un file .py');
    else if (redir) motivi.push('heredoc o redirezione verso python');
    else if (soloOpzioni) motivi.push('python senza script apre la REPL');
  }

  if (motivi.length === 0) process.exit(0);

  process.stderr.write(
    'Python da stdin è vietato in questo progetto (' + [...new Set(motivi)].join('; ') + ').\n' +
    'Scrivi lo script in un file (nello scratchpad) e lancialo con: python -I <file.py>\n'
  );
  process.exit(2);
});
