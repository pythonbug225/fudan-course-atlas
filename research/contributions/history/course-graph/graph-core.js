(function (root) {
  'use strict';
  function ancestors(data, id) {
    const result = new Set([id]), todo = [id];
    while (todo.length) {
      const current = todo.pop();
      for (const edge of data.edges) {
        if (edge.type === 'recommended_prerequisite' && edge.target === current && !result.has(edge.source)) {
          result.add(edge.source); todo.push(edge.source);
        }
      }
    }
    return result;
  }
  function select(data, options) {
    const permitted = data.edges.filter(e => options.type === 'all' || e.type === options.type);
    let ids;
    if (options.mode === 'ancestors') ids = ancestors(data, options.focus);
    else if (options.path) ids = new Set(data.paths.find(p => p.id === options.path)?.codes || []);
    else if (options.mode === 'focus') {
      ids = new Set([options.focus]);
      for (const edge of permitted) if (edge.source === options.focus || edge.target === options.focus) {
        ids.add(edge.source); ids.add(edge.target);
      }
    } else ids = new Set(data.nodes.map(n => n.id));
    const nodes = data.nodes.filter(n => ids.has(n.id) &&
      (options.group === 'all' || options.group === n.group) &&
      (options.level === 'all' || (options.level === 'ug' ? n.levels.some(l => l === '本科' || l === '本研融通') : n.levels.includes(options.level))));
    ids = new Set(nodes.map(n => n.id));
    let edges = permitted.filter(e => ids.has(e.source) && ids.has(e.target));
    if (options.mode === 'ancestors') edges = edges.filter(e => e.type === 'recommended_prerequisite');
    return {nodes, edges};
  }
  function search(data, query) {
    const term = query.trim().toLocaleLowerCase();
    return data.nodes.filter(n => [n.id, ...n.names, ...n.teachers].some(x => x.toLocaleLowerCase().includes(term)));
  }
  const api = {ancestors, select, search};
  if (typeof module !== 'undefined' && module.exports) module.exports = api;
  else root.HistoryGraph = api;
})(globalThis);
