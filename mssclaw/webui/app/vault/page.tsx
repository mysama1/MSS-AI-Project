// mssclaw WebUI — Vault Dashboard
// 吸收模式: Dashboard Starter (table, search, KBar navigation)

"use client";

import { useState, useMemo } from "react";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Search, Plus, Download, Trash2, Copy, Eye, EyeOff } from "lucide-react";

interface VaultEntry {
  id: string;
  service: string;
  username: string;
  password: string;
  url?: string;
  category?: string;
  created: string;
}

// Mock data — in production, fetches from mssclaw vault API
const MOCK_ENTRIES: VaultEntry[] = [
  { id: "1", service: "GitHub", username: "mysama1", password: "••••••••", url: "https://github.com", category: "dev", created: "2026-01-15" },
  { id: "2", service: "PyPI", username: "mysama1", password: "••••••••", url: "https://pypi.org", category: "dev", created: "2026-02-01" },
  { id: "3", service: "OpenAI", username: "admin@mss.ai", password: "••••••••", url: "https://platform.openai.com", category: "api", created: "2026-03-10" },
];

export default function VaultPage() {
  const [search, setSearch] = useState("");
  const [showPassword, setShowPassword] = useState<Record<string, boolean>>({});

  const filtered = useMemo(
    () =>
      MOCK_ENTRIES.filter(
        (e) =>
          e.service.toLowerCase().includes(search.toLowerCase()) ||
          e.username.toLowerCase().includes(search.toLowerCase())
      ),
    [search]
  );

  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between">
        <h2 className="text-2xl font-bold">Vault</h2>
        <Button>
          <Plus className="mr-2 h-4 w-4" />
          Add Entry
        </Button>
      </div>

      {/* Search bar — 吸收自 Dashboard Starter */}
      <div className="relative">
        <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
        <Input
          placeholder="Search by service or username..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          className="pl-10"
        />
      </div>

      {/* Table — 吸收自 Dashboard Starter table component */}
      <div className="rounded-md border">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Service</TableHead>
              <TableHead>Username</TableHead>
              <TableHead>Password</TableHead>
              <TableHead>Category</TableHead>
              <TableHead className="w-[100px]">Actions</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {filtered.map((entry) => (
              <TableRow key={entry.id}>
                <TableCell className="font-medium">{entry.service}</TableCell>
                <TableCell>{entry.username}</TableCell>
                <TableCell>
                  <div className="flex items-center gap-2">
                    <span className="font-mono">
                      {showPassword[entry.id] ? entry.password : "••••••••"}
                    </span>
                    <Button
                      variant="ghost"
                      size="icon"
                      onClick={() =>
                        setShowPassword((prev) => ({
                          ...prev,
                          [entry.id]: !prev[entry.id],
                        }))
                      }
                    >
                      {showPassword[entry.id] ? (
                        <EyeOff className="h-4 w-4" />
                      ) : (
                        <Eye className="h-4 w-4" />
                      )}
                    </Button>
                  </div>
                </TableCell>
                <TableCell>
                  <span className="rounded-full bg-secondary px-2 py-1 text-xs">
                    {entry.category}
                  </span>
                </TableCell>
                <TableCell>
                  <div className="flex gap-1">
                    <Button variant="ghost" size="icon" title="Copy">
                      <Copy className="h-4 w-4" />
                    </Button>
                    <Button variant="ghost" size="icon" title="Delete">
                      <Trash2 className="h-4 w-4 text-destructive" />
                    </Button>
                  </div>
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </div>

      {/* Stats footer */}
      <div className="flex justify-between text-sm text-muted-foreground">
        <span>{filtered.length} entries</span>
        <Button variant="outline" size="sm">
          <Download className="mr-2 h-4 w-4" />
          Export
        </Button>
      </div>
    </div>
  );
}
