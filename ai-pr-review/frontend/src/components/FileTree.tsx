'use client';

import { useState } from 'react';
import type { ReviewComment, ReviewFile } from '@/types/review';
import { Severity } from '@/types/review';

interface FileTreeNode {
  name: string;
  path: string;
  isDir: boolean;
  children: FileTreeNode[];
  issues: ReviewComment[];
  fileInfo?: ReviewFile;
}

interface FileTreeProps {
  files: ReviewFile[];
  comments: ReviewComment[];
  activeFile: string | null;
  onFileSelect: (filePath: string) => void;
}

function buildTree(files: ReviewFile[], comments: ReviewComment[]): FileTreeNode[] {
  const commentsByPath: Record<string, ReviewComment[]> = {};
  for (const c of comments) {
    if (!commentsByPath[c.file_path]) commentsByPath[c.file_path] = [];
    commentsByPath[c.file_path].push(c);
  }

  const fileInfoByPath: Record<string, ReviewFile> = {};
  for (const f of files) {
    fileInfoByPath[f.file_path] = f;
  }

  const root: FileTreeNode[] = [];
  const dirMap: Record<string, FileTreeNode> = {};

  for (const f of files) {
    const parts = f.file_path.split('/');
    let currentParts: string[] = [];
    let currentChildren = root;

    for (let i = 0; i < parts.length; i++) {
      const part = parts[i]!;
      currentParts.push(part);
      const fullPath = currentParts.join('/');
      const isLast = i === parts.length - 1;

      if (isLast) {
        currentChildren.push({
          name: part,
          path: fullPath,
          isDir: false,
          children: [],
          issues: commentsByPath[f.file_path] ?? [],
          fileInfo: f,
        });
      } else {
        let dir = dirMap[fullPath];
        if (!dir) {
          dir = {
            name: part,
            path: fullPath,
            isDir: true,
            children: [],
            issues: [],
          };
          dirMap[fullPath] = dir;
          currentChildren.push(dir);
        }
        currentChildren = dir.children;
      }
    }
  }

  return root;
}

function severityDot(severity: string): string {
  switch (severity) {
    case 'critical': return '🔴';
    case 'major': return '🟠';
    case 'minor': return '🟡';
    default: return '⚪';
  }
}

export function FileTree({ files, comments, activeFile, onFileSelect }: FileTreeProps) {
  const [collapsed, setCollapsed] = useState<Set<string>>(new Set());
  const tree = buildTree(files, comments);

  const toggleDir = (path: string) => {
    setCollapsed((prev) => {
      const next = new Set(prev);
      if (next.has(path)) next.delete(path);
      else next.add(path);
      return next;
    });
  };

  const renderNode = (node: FileTreeNode, depth: number) => {
    const isCollapsed = collapsed.has(node.path);
    const isActive = node.path === activeFile;
    const criticalCount = node.issues.filter((i) => i.severity === 'critical').length;
    const totalIssues = node.issues.length;

    return (
      <div key={node.path}>
        {node.isDir ? (
          <div
            className="flex cursor-pointer items-center gap-1 rounded px-2 py-1 text-sm text-gray-700 hover:bg-gray-100"
            style={{ paddingLeft: `${depth * 16 + 8}px` }}
            onClick={() => toggleDir(node.path)}
          >
            <span className="w-4 text-center">{isCollapsed ? '▶' : '▼'}</span>
            <span className="font-medium">📁 {node.name}</span>
          </div>
        ) : (
          <div
            className={`flex cursor-pointer items-center gap-1 rounded px-2 py-1 text-sm ${
              isActive ? 'bg-blue-100 text-blue-800' : 'text-gray-700 hover:bg-gray-50'
            }`}
            style={{ paddingLeft: `${depth * 16 + 8}px` }}
            onClick={() => onFileSelect(node.path)}
          >
            <span className="w-4 text-center">📄</span>
            <span className="flex-1 truncate">{node.name}</span>
            {totalIssues > 0 && (
              <span className="flex items-center gap-0.5 text-xs">
                {criticalCount > 0 && <span>{severityDot('critical')}{criticalCount}</span>}
                <span className="text-gray-400">({totalIssues})</span>
              </span>
            )}
            {node.fileInfo && (
              <span className="text-xs text-gray-400">
                +{node.fileInfo.additions}/-{node.fileInfo.deletions}
              </span>
            )}
          </div>
        )}
        {node.isDir && !isCollapsed && node.children.map((child) => renderNode(child, depth + 1))}
      </div>
    );
  };

  return (
    <div className="overflow-y-auto rounded-lg border border-gray-200 bg-gray-50 p-2">
      {tree.length === 0 ? (
        <p className="px-2 py-4 text-center text-sm text-gray-400">无文件变更</p>
      ) : (
        tree.map((node) => renderNode(node, 0))
      )}
    </div>
  );
}
