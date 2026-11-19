const unique = values => [...new Set(values)];
const normalizeCode = code => code.toUpperCase();

export function mergeTermOfferings(catalog, details, snapshot) {
  const { term, queriedOn, courses } = snapshot;
  const cardsByCode = new Map();

  for (const card of catalog.courses) {
    const code = normalizeCode(card.code);
    if (!cardsByCode.has(code)) cardsByCode.set(code, []);
    cardsByCode.get(code).push(card);
  }

  let sectionCount = 0;
  for (const { code, name, sections } of courses) {
    const matches = cardsByCode.get(normalizeCode(code)) ?? [];
    let card = matches.find(match => match.name === name) ?? matches[0];
    if (!card) {
      card = {
        id: 'S27-' + code, code, name, teachers: [], departments: [], terms: [],
        categories: [], credits: [], aliases: [], has_reviews: false, plan_only: false, plans: [],
      };
      catalog.courses.push(card);
      details[card.id] = { sections: [], evidence: [] };
    }

    card.teachers = unique([...card.teachers, ...sections.flatMap(section => section.teachers)]);
    card.departments = unique([...card.departments, ...sections.map(section => section.department).filter(Boolean)]);
    card.categories = unique([...card.categories, ...sections.map(section => section.category).filter(Boolean)]);
    card.credits = unique([...card.credits, ...sections.map(section => section.credits)]).sort((a, b) => a - b);
    card.terms = unique([...card.terms, term]);
    card.plan_only = false;
    if (name !== card.name) card.aliases = unique([...card.aliases, name]);

    const added = sections.map(section => ({
      ...section,
      term,
      assessment: [],
      source: `复旦教务公开全校开课查询 · ${term} · ${queriedOn} · ${section.code}`,
      sourceUrl: snapshot.source,
    }));
    const detail = details[card.id];
    detail.sections = [...detail.sections.filter(section => section.term !== term), ...added];
    sectionCount += added.length;
  }

  catalog.stats.courses = catalog.courses.length;
  catalog.stats.sections = Object.values(details).reduce((count, detail) => count + detail.sections.length, 0);
  catalog.snapshot += `；${term}教务快照（${queriedOn}，${sectionCount} 个教学班）`;
}
