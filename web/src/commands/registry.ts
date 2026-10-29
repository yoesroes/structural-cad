/**
 * Registri perintah menu — logika murni, tanpa React.
 * state = { hasProject, dirty, hasElementFile }
 */

export interface CommandState {
  hasProject: boolean;
  dirty: boolean;
  hasElementFile: boolean;
}

export interface CommandDef {
  id: string;
  label: string;
  /** jalur menu, mis. ["File", "Project", "Simpan"] */
  menu: string[];
  shortcut?: string;
  enabled: (state: CommandState) => boolean;
}

export interface MenuItem {
  id?: string;
  label: string;
  enabled: boolean;
  shortcut?: string;
  children?: MenuItem[];
}

/** Daftar perintah yang dikenal aplikasi. */
export const COMMANDS: CommandDef[] = [
  // File > Project
  {
    id: "project.new",
    label: "Baru…",
    menu: ["File", "Project", "Baru…"],
    enabled: () => true,
  },
  {
    id: "project.open",
    label: "Buka…",
    menu: ["File", "Project", "Buka…"],
    enabled: () => true,
  },
  {
    id: "project.save",
    label: "Simpan",
    menu: ["File", "Project", "Simpan"],
    shortcut: "Ctrl+S",
    enabled: (s) => s.hasProject && s.dirty,
  },
  {
    id: "project.saveAs",
    label: "Simpan Sebagai…",
    menu: ["File", "Project", "Simpan Sebagai…"],
    enabled: (s) => s.hasProject,
  },
  // File > File Elemen
  {
    id: "element.new",
    label: "Baru…",
    menu: ["File", "File Elemen", "Baru…"],
    enabled: () => true,
  },
  {
    id: "element.open",
    label: "Buka…",
    menu: ["File", "File Elemen", "Buka…"],
    enabled: () => true,
  },
  {
    id: "element.save",
    label: "Simpan",
    menu: ["File", "File Elemen", "Simpan"],
    enabled: (s) => s.hasElementFile && s.dirty,
  },
  {
    id: "element.saveAs",
    label: "Simpan Sebagai…",
    menu: ["File", "File Elemen", "Simpan Sebagai…"],
    enabled: (s) => s.hasElementFile,
  },
  // File (root actions)
  {
    id: "project.addElementFile",
    label: "Tambahkan File Elemen ke Project…",
    menu: ["File", "Tambahkan File Elemen ke Project…"],
    enabled: (s) => s.hasProject,
  },
  {
    id: "project.updateDefinitionFromFile",
    label: "Perbarui Definisi dari File…",
    menu: ["File", "Perbarui Definisi dari File…"],
    enabled: (s) => s.hasProject,
  },
  // Menu lain — judul saja, belum aktif
  {
    id: "elemen.placeholder",
    label: "Elemen",
    menu: ["Elemen"],
    enabled: () => false,
  },
  {
    id: "tulangan.placeholder",
    label: "Tulangan",
    menu: ["Tulangan"],
    enabled: () => false,
  },
  {
    id: "periksa.placeholder",
    label: "Periksa",
    menu: ["Periksa"],
    enabled: () => false,
  },
  {
    id: "ekspor.placeholder",
    label: "Ekspor",
    menu: ["Ekspor"],
    enabled: () => false,
  },
];

/**
 * Bangun pohon menu dari COMMANDS + state.
 * Item tanpa anak yang disabled tetap muncul dengan enabled=false.
 */
export function buildMenu(state: CommandState): MenuItem[] {
  type Node = { label: string; id?: string; shortcut?: string; enabled: boolean; children?: Map<string, Node> };
  const roots = new Map<string, Node>();

  for (const cmd of COMMANDS) {
    const path = cmd.menu;
    if (path.length === 0) continue;

    let map = roots;
    let node: Node | undefined;

    for (let i = 0; i < path.length; i++) {
      const label = path[i];
      const isLeaf = i === path.length - 1;
      if (!map.has(label)) {
        map.set(label, {
          label,
          enabled: true,
          children: isLeaf ? undefined : new Map(),
        });
      }
      node = map.get(label)!;
      if (isLeaf) {
        node.id = cmd.id;
        node.shortcut = cmd.shortcut;
        node.enabled = cmd.enabled(state);
        node.children = undefined;
      } else {
        if (!node.children) node.children = new Map();
        map = node.children;
      }
    }
  }

  function toItems(m: Map<string, Node>): MenuItem[] {
    return Array.from(m.values()).map((n) => {
      const item: MenuItem = {
        label: n.label,
        enabled: n.enabled,
      };
      if (n.id) item.id = n.id;
      if (n.shortcut) item.shortcut = n.shortcut;
      if (n.children && n.children.size > 0) {
        item.children = toItems(n.children);
        // Parent enabled jika ada anak yang enabled (atau selalu true untuk navigasi)
        item.enabled = item.children.some((c) => c.enabled) || item.children.length > 0;
      }
      return item;
    });
  }

  return toItems(roots);
}
