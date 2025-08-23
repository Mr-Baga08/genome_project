const settingsMenuItems = [
  {
    name: 'Preferences...',
    action: () => alert('Preferences clicked!'),
  },
  {
    name: 'Plugins...',
    action: () => alert('Plugins clicked!'),
  },
];

const toolsMenuItems = [
  {
    name: 'Sanger data analysis',
    action: () => alert('Open File clicked!'),
  },
  {
    name: 'NGS data analysis',
    action: () => alert('Exit clicked!'),
  },
  {
    name: 'BLAST',
    action: () => alert('Open File clicked!'),
  },
  {
    name: 'Multiple sequence analysis',
    action: () => alert('Save File clicked!'),
  },
  {
    name: 'Cloning',
    action: () => alert('Exit clicked!'),
  },
  { name: 'Primer', action: () => alert('Open File clicked!') },
  { name: 'Search for TFBS', action: () => alert('Save File clicked!') },
  {
    name: 'HMMER tools',
    action: () => alert('Exit clicked!'),
  },
  {
    name: 'Build dotplot...',
    action: () => alert('Save File clicked!'),
  },
  {
    name: 'Random sequence generator...',
    action: () => alert('Exit clicked!'),
  },
  {
    name: 'Query designer...',
    action: () => alert('Open File clicked!'),
  },
  {
    name: 'Workflow designer...',
    action: () => alert('Save File clicked!'),
  },
];

const helpMenuItems = [
  {
    name: 'View UGENE Documentation Online',
    action: () =>
      window.open(
        'https://ugene.net/documentation',
        '_blank',
        'noopener noreferrer',
      ),
  },
  {
    name: 'Visit UGENE Website',
    action: () =>
      window.open('https://ugene.net', '_blank', 'noopener noreferrer'),
  },
  {
    name: "What's New in UGENE",
    action: () => alert('Feature under development.'),
  },
  { name: 'Check for Updates', action: () => alert('No updates available.') },
  { name: 'BookMark', action: () => alert('Bookmark added.') },
  {
    name: 'Support UGENE on Patreon',
    action: () =>
      window.open('https://www.patreon.com', '_blank', 'noopener noreferrer'),
  },
  { name: 'Open Start Page', action: () => alert('Start page opened.') },
  { name: 'About', action: () => alert('UGENE version 1.0.0.') },
];

const fileMenuItems = [
  { name: 'New project' },
  {
    name: 'New documentation from text',
    action: () => alert('Save File clicked!'),
  },
  {
    name: 'New workflow',
  },
  {
    name: 'Open..',
    action: () => alert('Open File clicked!'),
  },
  {
    name: 'Open as...',
    action: () => alert('Save File clicked!'),
  },
  {
    name: 'Open from clipboard',
    action: () => alert('Exit clicked!'),
  },
  {
    name: 'Log in to Workspace',
    action: () => alert('Open File clicked!'),
  },
  {
    name: 'Access remote database',
    action: () => alert('Save File clicked!'),
  },
  {
    name: 'Search NCBI GenBank',
    action: () => alert('Exit clicked!'),
  },
  {
    name: 'Recent files',
    submenu: [{ name: 'Recent file', type: 'link' }],
  },
  { name: 'Recent projects', action: () => alert('Save File clicked!') },
  {
    name: 'Save all',
    action: () => alert('Exit clicked!'),
  },
  { name: 'Save project as..', action: () => alert('Open File clicked!') },
  { name: 'Export project', action: () => alert('Save File clicked!') },
  { name: 'Close project' },
  { name: 'Exit' },
];

const actionsMenuItems = [
  {
    name: 'Add element',
    submenu: [
      {
        name: 'Data Readers',
        submenu: [
          {
            name: 'Read Alignment',
            type: 'link',
          },
          {
            name: 'Read Annotations',
            type: 'link',
          },
          {
            name: 'Read FASTQ File with SE Reads',
            type: 'link',
          },
          {
            name: 'Read FASTQ File with PE Reads',
            type: 'link',
          },
          {
            name: 'Read File URL(s)',
            type: 'link',
          },
          {
            name: 'Read NGS Reads Assembly',
            type: 'link',
          },
          {
            name: 'Read Plain Text',
            type: 'link',
          },
          {
            name: 'Read Sequence',
            type: 'link',
          },
          {
            name: 'Read Sequence from Remote Database',
            type: 'link',
          },
          {
            name: 'Read Variants',
            type: 'link',
          },
        ],
      },
      {
        name: 'Data Writers',
        submenu: [
          { name: 'Read Alignment', icon: './images/teal.png', type: 'link' },
          {
            name: 'Read Annotations',
            type: 'link',
          },
          {
            name: 'Read FASTQ File with SE Reads',
            type: 'link',
          },
          {
            name: 'Read FASTQ File with PE Reads',
            type: 'link',
          },
          {
            name: 'Read File URL(s)',
            type: 'link',
          },
          {
            name: 'Read NGS Reads Assembly',
            type: 'link',
          },
          {
            name: 'Read Plain Text',
            type: 'link',
          },
        ],
      },
      { name: 'Basic Analysis', type: 'link' },
      {
        name: 'DNA Assembly',
        submenu: [
          {
            name: 'Assembly sequences with CAP3',
            type: 'link',
          },
        ],
      },
      {
        name: 'Data Converters',
        submenu: [
          {
            name: 'Convert Text to Sequence',
            type: 'link',
          },
          {
            name: 'Convert bedGraph files to bigWig',
            type: 'link',
          },
          {
            name: 'File Format conversion',
            type: 'link',
          },
          {
            name: 'Reverse Complement',
            type: 'link',
          },
          {
            name: 'Split Assembly into sequences',
            type: 'link',
          },
        ],
      },
      {
        name: 'Data Flow',
        submenu: [
          { name: 'Filter', icon: './images/teal.png', type: 'link' },
          { name: 'Grouper', icon: './images/teal.png', type: 'link' },
          { name: 'Multiplexer', icon: './images/teal.png', type: 'link' },
          {
            name: 'Sequence Marker',
            type: 'link',
          },
        ],
      },
      {
        name: 'HMMER2 Tools',
        submenu: [
          { name: 'HMMER2 Build', icon: './images/teal.png', type: 'link' },
          { name: 'HMMER2 Search', icon: './images/teal.png', type: 'link' },
          {
            name: 'Read HMMER2 Profile',
            type: 'link',
          },
          {
            name: 'Write HMMER2 Profile',
            type: 'link',
          },
        ],
      },
      { name: 'HMMER3 Tools', type: 'link' },
      { name: 'Includes', type: 'link' },
      { name: 'Multiple Sequence Allignment', type: 'link' },
      { name: 'NGS: Basic functions', type: 'link' },
      { name: 'NGS: Map Assemble reads', type: 'link' },
      { name: 'NGS: RNA Seq Analysis', type: 'link' },
      { name: 'NGS: Variant Analysis', type: 'link' },
      { name: 'Transcription Factor Binding Sites', type: 'link' },
      { name: 'Utils', type: 'link' },
      {
        name: 'Custom Element With Script',
        submenu: [
          { name: 'Data Readers', type: 'link' },
          { name: 'Data Writers', type: 'link' },
          { name: 'Basic Analysis', type: 'link' },
          { name: 'DNA Assembly', type: 'link' },
          { name: 'Data Converters', type: 'link' },
          { name: 'Data Flow', type: 'link' },
          { name: 'HMMER2 Tools', type: 'link' },
          { name: 'HMMER3 Tools', type: 'link' },
          { name: 'Includes', type: 'link' },
          { name: 'Multiple Sequence Allignment', type: 'link' },
          { name: 'NGS: Basic functions', type: 'link' },
          { name: 'NGS: Map Assemble reads', type: 'link' },
          { name: 'NGS: RNA Seq Analysis', type: 'link' },
          { name: 'NGS: Variant Analysis', type: 'link' },
          { name: 'Transcription Factor Binding Sites', type: 'link' },
          { name: 'Utils', type: 'link' },
          { name: 'Custom Element With Script', type: 'link' },
        ],
      },
    ],
  },
  {
    name: 'Copy',
    action: () => alert('Save File clicked!'),
  },
  {
    name: 'Paste',
    action: () => alert('Exit clicked!'),
  },
  {
    name: 'Cut',
    action: () => alert('Open File clicked!'),
  },
  { name: 'Delete' },
  { name: 'Select all elements', action: () => alert('Exit clicked!') },
  {
    name: 'New workflow...',
  },
  {
    name: 'Load workflow',
    action: () => alert('Save File clicked!'),
  },
  {
    name: 'Save workflow',
    action: () => alert('Exit clicked!'),
  },
  {
    name: 'Save workflow as...',
    action: () => alert('Exit clicked!'),
  },
  {
    name: 'Export workflow as image',
    action: () => alert('Exit clicked!'),
  },
  {
    name: 'Validate workflow',
    action: () => alert('Exit clicked!'),
  },
  {
    name: 'Run workflow',
    action: () => alert('Exit clicked!'),
  },
  {
    name: 'Set parameter aliases...',
    action: () => alert('Exit clicked!'),
  },
  {
    name: 'Create galaxy tool config...',
    action: () => alert('Exit clicked!'),
  },
  {
    name: 'Create element with script...',
    action: () => alert('Exit clicked!'),
  },
  {
    name: 'Edit script of the element...',
    action: () => alert('Open File clicked!'),
  },
  {
    name: 'Create element with external tool...',
    action: () => alert('Save File clicked!'),
  },
  {
    name: 'Add element with external tool...',
    action: () => alert('Exit clicked!'),
  },
  { name: 'Element style', action: () => alert('Open File clicked!') },
  { name: 'Scripting mode', action: () => alert('Save File clicked!') },
  {
    name: 'Dashboards manager',
    action: () => alert('Exit clicked!'),
  },
  { name: 'Close active view', action: () => alert('Exit clicked!') },
];

const windowMenuItems = [
  { name: 'Close active window', action: () => alert('close all windows') },
  { name: 'Close all windows', action: () => alert('close all windows') },
  {
    name: 'Tile windows',
    action: () => alert('Setting tile windows'),
  },
  {
    name: 'Cascade windows',
    action: () => alert('Setting cascade windows'),
  },
  {
    name: 'Next window',
    action: () => alert('Clicked Next window'),
  },
  {
    name: 'Previous window',
    action: () => alert('Clicked Previous window'),
  },
  { name: '1 StartPage', action: () => alert('Start Page') },
  {
    name: '2 Workflow Designer - New workflow',
    action: () => alert('Workflow Designer - New workflow'),
  },
  {
    name: '3 Workflow Designer - New workflow',
    action: () => alert('Workflow Designer - New workflow'),
  },
  {
    name: '4 Workflow Designer - New workflow',
    action: () => alert('Workflow Designer - New workflow'),
  },
];

const menuItems = {
  file: fileMenuItems,
  actions: actionsMenuItems,
  settings: settingsMenuItems,
  tools: toolsMenuItems,
  window: windowMenuItems,
  help: helpMenuItems,
};

export default menuItems;