import * as vscode from 'vscode';
import { spawn } from 'child_process';
import * as path from 'path';

function workspacePath(): string {
  const folders = vscode.workspace.workspaceFolders;
  if (!folders || folders.length === 0) {
    throw new Error('No workspace opened.');
  }
  return folders[0].uri.fsPath;
}

function agentPath(context: vscode.ExtensionContext): string {
  const configured = vscode.workspace.getConfiguration('reqsysAgent').get<string>('agentPath') || '';
  return configured || path.resolve(context.extensionPath, '..', 'agent');
}

function runAgent(context: vscode.ExtensionContext, args: string[]): Promise<string> {
  const pythonPath = vscode.workspace.getConfiguration('reqsysAgent').get<string>('pythonPath') || 'python';
  const cwd = agentPath(context);

  return new Promise((resolve, reject) => {
    const child = spawn(pythonPath, ['-m', 'reqsys_agent.cli', ...args], {
      cwd,
      env: { ...process.env, PYTHONPATH: cwd }
    });

    let stdout = '';
    let stderr = '';

    child.stdout.on('data', chunk => stdout += chunk.toString());
    child.stderr.on('data', chunk => stderr += chunk.toString());
    child.on('error', reject);
    child.on('close', code => {
      if (code === 0) {
        resolve(stdout);
      } else {
        reject(new Error(stderr || stdout));
      }
    });
  });
}

function escapeHtml(content: string): string {
  return content.replace(/&/g, '&amp;').replace(/</g, '&lt;');
}

function showDocument(title: string, content: string): void {
  const panel = vscode.window.createWebviewPanel('reqsysAgent', title, vscode.ViewColumn.One, {
    enableScripts: false
  });

  panel.webview.html = `<!DOCTYPE html>
<html lang="pt-BR">
<body style="font-family: system-ui, sans-serif; padding: 16px;">
<h1>${title}</h1>
<pre style="white-space: pre-wrap; background: #f6f8fa; padding: 12px; border-radius: 8px;">${escapeHtml(content)}</pre>
</body>
</html>`;
}

async function runAndShow(context: vscode.ExtensionContext, title: string, args: string[]): Promise<void> {
  try {
    showDocument(title, await runAgent(context, args));
  } catch (error) {
    const message = error instanceof Error ? error.message : String(error);
    vscode.window.showErrorMessage(`ReqSys Agent: ${message}`);
  }
}

async function promptQuestion(title: string, placeHolder: string): Promise<string | undefined> {
  const question = await vscode.window.showInputBox({
    title,
    prompt: 'Digite uma pergunta baseada no contexto local indexado',
    placeHolder
  });

  if (!question || question.trim().length === 0) {
    return undefined;
  }

  return question;
}

export function activate(context: vscode.ExtensionContext): void {
  context.subscriptions.push(vscode.commands.registerCommand('reqsysAgent.health', async () => {
    await runAndShow(context, 'ReqSys Agent Health', ['health']);
  }));

  context.subscriptions.push(vscode.commands.registerCommand('reqsysAgent.inspect', async () => {
    await runAndShow(context, 'ReqSys Agent Inspect', ['inspect', '--workspace', workspacePath()]);
  }));

  context.subscriptions.push(vscode.commands.registerCommand('reqsysAgent.governance', async () => {
    await runAndShow(context, 'ReqSys Agent Governance', ['governance', '--workspace', workspacePath()]);
  }));

  context.subscriptions.push(vscode.commands.registerCommand('reqsysAgent.buildIndex', async () => {
    await runAndShow(context, 'ReqSys Agent Local Context', ['build-index', '--workspace', workspacePath()]);
  }));

  context.subscriptions.push(vscode.commands.registerCommand('reqsysAgent.ask', async () => {
    const question = await promptQuestion('ReqSys Agent: Ask Local Context', 'Quais workflows existem?');
    if (!question) {
      return;
    }
    await runAndShow(context, 'ReqSys Agent Ask', ['ask', '--workspace', workspacePath(), '--question', question]);
  }));

  context.subscriptions.push(vscode.commands.registerCommand('reqsysAgent.semanticAsk', async () => {
    const question = await promptQuestion('ReqSys Agent: Semantic Ask Local Context', 'controle de qualidade de pipelines');
    if (!question) {
      return;
    }
    await runAndShow(context, 'ReqSys Agent Semantic Ask', ['semantic-ask', '--workspace', workspacePath(), '--question', question]);
  }));

  context.subscriptions.push(vscode.commands.registerCommand('reqsysAgent.index', async () => {
    showDocument('ReqSys Agent Index', await runAgent(context, ['index', '--workspace', workspacePath()]));
  }));
}

export function deactivate(): void {}
