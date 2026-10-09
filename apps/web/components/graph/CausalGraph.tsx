"use client";

import cytoscape, { type Core, type ElementDefinition } from "cytoscape";
import { useEffect, useMemo, useRef, useState } from "react";

import { API_URL } from "@/lib/api";
import type {
  BiologicalEntity,
  CausalAssertion,
  EvidenceRecord,
  InvestigationResult,
} from "@/lib/types";
import { humanize, representativePath } from "@/lib/presentation";
import { initialGraphNodes, expandGraphNodes } from "@/lib/graph-view";
import { EvidenceCard } from "@/components/EvidenceDetails";

const NODE_COLORS: Record<string, string> = {
  cognitive_outcome: "#a18c6c",
  symptom: "#a3776d",
  disease_or_condition: "#928091",
  tissue: "#78909c",
  cell_type: "#809993",
  receptor: "#88849d",
  protein: "#88849d",
  biological_process: "#7b9584",
  behavior: "#a39876",
  biomechanical_force: "#7a92a2",
  therapy: "#a08976",
  device: "#8c8d9f",
  experimental_compound: "#988294",
  neurotransmitter: "#94879f",
  phenotype: "#8a9680",
  immune_mediator: "#a1867a",
};

export function CausalGraph({
  result,
  initialHypothesisId,
}: {
  result: InvestigationResult;
  initialHypothesisId?: string | undefined;
}) {
  const containerRef = useRef<HTMLDivElement>(null);
  const cyRef = useRef<Core | null>(null);
  const [entityType, setEntityType] = useState("all");
  const [relation, setRelation] = useState("all");
  const [grade, setGrade] = useState("all");
  const [organism, setOrganism] = useState("all");
  const [scope, setScope] = useState(() => initialGraphNodes(result, initialHypothesisId));
  const [tissue, setTissue] = useState("all");
  const [causalStatus, setCausalStatus] = useState("all");
  const [interventionClass, setInterventionClass] = useState("all");
  const [studiesOpen, setStudiesOpen] = useState(false);
  const [search, setSearch] = useState("");
  const [pathId, setPathId] = useState(initialHypothesisId ?? result.hypotheses[0]?.id ?? "all");
  const [selectedAssertionId, setSelectedAssertionId] = useState<string | null>(null);
  const [selectedEntityId, setSelectedEntityId] = useState<string | null>(null);

  const entityLookup = useMemo(
    () => new Map(result.graph.entities.map((entity) => [entity.id, entity])),
    [result.graph.entities],
  );
  const assertionLookup = useMemo(
    () => new Map(result.graph.assertions.map((assertion) => [assertion.id, assertion])),
    [result.graph.assertions],
  );
  const evidenceLookup = useMemo(
    () => new Map(result.graph.evidence.map((record) => [record.id, record])),
    [result.graph.evidence],
  );

  const options = useMemo(() => {
    const entityTypes = [
      ...new Set(result.graph.entities.map((entity) => entity.entity_type)),
    ].sort();
    const relations = [
      ...new Set(result.graph.assertions.map((assertion) => assertion.relation)),
    ].sort();
    const organisms = [
      ...new Set(result.graph.assertions.map((assertion) => assertion.biological_context.species)),
    ].sort();
    return { entityTypes, relations, organisms };
  }, [result.graph]);

  const visible = useMemo(() => {
    const assertions = result.graph.assertions.filter((assertion) => {
      if (!scope.includes(assertion.subject_id) || !scope.includes(assertion.object_id))
        return false;
      if (tissue !== "all" && assertion.biological_context.tissue !== tissue) return false;
      if (causalStatus !== "all" && assertion.causal_status !== causalStatus) return false;
      if (
        interventionClass !== "all" &&
        !result.interventions.some(
          (item) =>
            item.intervention_class === interventionClass &&
            (item.target_entity_ids.includes(assertion.subject_id) ||
              item.target_entity_ids.includes(assertion.object_id) ||
              item.downstream_assertion_ids.includes(assertion.id)),
        )
      )
        return false;
      const subject = entityLookup.get(assertion.subject_id);
      const object = entityLookup.get(assertion.object_id);
      if (
        entityType !== "all" &&
        subject?.entity_type !== entityType &&
        object?.entity_type !== entityType
      )
        return false;
      if (relation !== "all" && assertion.relation !== relation) return false;
      if (grade !== "all" && assertion.confidence_classification !== grade) return false;
      if (organism !== "all" && assertion.biological_context.species !== organism) return false;
      return true;
    });
    const nodeIds = new Set(
      assertions.flatMap((assertion) => [assertion.subject_id, assertion.object_id]),
    );
    return {
      assertions,
      entities: result.graph.entities.filter((entity) => nodeIds.has(entity.id)),
    };
  }, [
    entityLookup,
    entityType,
    grade,
    organism,
    relation,
    result.graph,
    scope,
    tissue,
    causalStatus,
    interventionClass,
    result.interventions,
  ]);

  const highlightedPath = useMemo(() => {
    const hypothesis = result.hypotheses.find((item) => item.id === pathId);
    return hypothesis ? (representativePath(hypothesis) ?? null) : null;
  }, [pathId, result.hypotheses]);

  useEffect(() => {
    if (!containerRef.current) return;
    const fontFamily = getComputedStyle(document.body).fontFamily;
    const pathNodes = new Set(highlightedPath?.entity_ids ?? []);
    const pathEdges = new Set(highlightedPath?.assertion_ids ?? []);
    const weakEdges = new Set(highlightedPath?.weak_link_assertion_ids ?? []);
    const elements: ElementDefinition[] = [
      ...visible.entities.map((entity) => ({
        group: "nodes" as const,
        data: {
          id: entity.id,
          label: entity.preferred_name,
          entityType: entity.entity_type,
          color: NODE_COLORS[entity.entity_type] ?? "#8a948b",
        },
        classes: pathNodes.has(entity.id) ? "path" : "",
      })),
      ...visible.assertions.map((assertion) => ({
        group: "edges" as const,
        data: {
          id: assertion.id,
          source: assertion.subject_id,
          target: assertion.object_id,
          label: `${humanize(assertion.relation)}${assertion.contradictory_evidence_ids.length ? " · conflicting evidence" : ""}`,
          relation: assertion.relation,
          grade: assertion.confidence_classification,
          causalStatus: assertion.causal_status,
          polarity: assertion.polarity,
          contradiction: assertion.contradictory_evidence_ids.length,
        },
        classes: `${pathEdges.has(assertion.id) ? "path" : ""} ${weakEdges.has(assertion.id) ? "weak" : ""}`,
      })),
    ];

    const cy = cytoscape({
      container: containerRef.current,
      elements,
      minZoom: 0.25,
      maxZoom: 2.4,
      style: [
        {
          selector: "node",
          style: {
            width: 34,
            height: 34,
            "background-color": "data(color)",
            label: "data(label)",
            color: "#20201d",
            "font-family": fontFamily,
            "font-size": 13,
            "font-weight": 500,
            "text-wrap": "wrap",
            "text-max-width": "150px",
            "text-valign": "bottom",
            "text-margin-y": 8,
            "border-width": 1,
            "border-color": "#68665f",
            "overlay-opacity": 0,
          },
        },
        {
          selector: "node[entityType = 'cognitive_outcome'], node[entityType = 'symptom']",
          style: { shape: "diamond" },
        },
        {
          selector: "node[entityType = 'tissue'], node[entityType = 'disease_or_condition']",
          style: { shape: "round-rectangle" },
        },
        { selector: "node[entityType = 'behavior']", style: { shape: "hexagon" } },
        {
          selector:
            "node[entityType = 'therapy'], node[entityType = 'device'], node[entityType = 'experimental_compound']",
          style: { shape: "tag" },
        },
        {
          selector: "edge",
          style: {
            width: 1.2,
            "line-color": "#8c8a82",
            "target-arrow-color": "#8c8a82",
            "target-arrow-shape": "triangle",
            "curve-style": "bezier",
            label: "data(label)",
            color: "#68665f",
            "font-family": fontFamily,
            "font-size": 11,
            "font-weight": 400,
            "text-background-color": "#fcfbf8",
            "text-background-opacity": 0.86,
            "text-background-padding": "2px",
            "text-rotation": "autorotate",
            "arrow-scale": 0.8,
            "overlay-opacity": 0,
          },
        },
        { selector: "edge[causalStatus *= 'association']", style: { "line-style": "dashed" } },
        {
          selector:
            "edge[causalStatus = 'computational_prediction'], edge[causalStatus = 'hypothesis_only']",
          style: { "line-style": "dotted" },
        },
        {
          selector: "edge[polarity = -1]",
          style: {
            "target-arrow-shape": "tee",
            "line-color": "#a34742",
            "target-arrow-color": "#a34742",
          },
        },
        {
          selector: "edge[contradiction > 0]",
          style: { "line-color": "#a34742", "target-arrow-color": "#a34742" },
        },
        {
          selector: "edge.path",
          style: {
            "line-color": "#8b713e",
            "target-arrow-color": "#8b713e",
            width: 2.2,
            "z-index": 10,
          },
        },
        { selector: "node.path", style: { "border-color": "#8b713e", "border-width": 2.5 } },
        {
          selector: "edge.weak",
          style: {
            "line-style": "dotted",
            "line-color": "#bf5b4e",
            "target-arrow-color": "#bf5b4e",
          },
        },
        {
          selector: ":selected",
          style: {
            "border-color": "#24483c",
            "border-width": 3,
            "line-color": "#24483c",
            "target-arrow-color": "#24483c",
          },
        },
      ],
      layout: {
        name: "breadthfirst",
        directed: true,
        spacingFactor: 1.4,
        padding: 40,
        animate: false,
      },
    });
    cy.on("tap", "edge", (event) => {
      setSelectedAssertionId(event.target.id());
      setSelectedEntityId(null);
    });
    cy.on("tap", "node", (event) => {
      setSelectedEntityId(event.target.id());
      setSelectedAssertionId(null);
    });
    function syncTheme() {
      const css = getComputedStyle(document.documentElement);
      cy.style()
        .selector("node")
        .style({ color: css.getPropertyValue("--ink").trim() })
        .selector("edge")
        .style({
          color: css.getPropertyValue("--ink-muted").trim(),
          "text-background-color": css.getPropertyValue("--surface").trim(),
        })
        .update();
    }
    syncTheme();
    const observer = new MutationObserver(syncTheme);
    observer.observe(document.documentElement, { attributes: true, attributeFilter: ["class"] });
    const resize = new ResizeObserver(() => {
      if (containerRef.current?.offsetWidth) {
        cy.resize();
        cy.fit(undefined, 40);
      }
    });
    resize.observe(containerRef.current);
    cyRef.current = cy;
    return () => {
      observer.disconnect();
      resize.disconnect();
      cyRef.current = null;
      cy.destroy();
    };
  }, [highlightedPath, visible]);

  function fit() {
    cyRef.current?.fit(undefined, 40);
  }

  function findNode() {
    const query = search.trim().toLowerCase();
    if (!query || !cyRef.current) return;
    const node = cyRef.current
      .nodes()
      .filter((item) => String(item.data("label")).toLowerCase().includes(query))[0];
    if (node) {
      cyRef.current.$(":selected").unselect();
      node.select();
      cyRef.current.center(node);
      cyRef.current.zoom(1.25);
      setSelectedEntityId(node.id());
      setSelectedAssertionId(null);
    }
  }

  function focusSelection() {
    if (selectedEntityId)
      setScope([
        selectedEntityId,
        ...result.graph.assertions
          .filter(
            (edge) => edge.subject_id === selectedEntityId || edge.object_id === selectedEntityId,
          )
          .flatMap((edge) => [edge.subject_id, edge.object_id]),
      ]);
  }
  function resetView() {
    setScope(initialGraphNodes(result, pathId));
    setEntityType("all");
    setRelation("all");
    setGrade("all");
    setOrganism("all");
    setTissue("all");
    setCausalStatus("all");
    setInterventionClass("all");
    setSelectedEntityId(null);
    setSelectedAssertionId(null);
  }
  function revealTypes(types: string[]) {
    setScope((current) => [
      ...new Set([
        ...current,
        ...result.graph.entities
          .filter((entity) => types.includes(entity.entity_type))
          .map((entity) => entity.id),
      ]),
    ]);
  }

  function exportVisible() {
    const payload = {
      investigation_id: result.id,
      visible_node_ids: visible.entities.map((entity) => entity.id),
      filters: {
        tissue,
        causal_status: causalStatus,
        intervention_class: interventionClass,
        entity_type: entityType,
        relation,
        grade,
        organism,
        hypothesis_path: pathId,
      },
      entities: visible.entities,
      assertions: visible.assertions,
    };
    const href = URL.createObjectURL(
      new Blob([JSON.stringify(payload, null, 2)], { type: "application/json" }),
    );
    const anchor = document.createElement("a");
    anchor.href = href;
    anchor.download = `causalbio-${result.id}-visible-graph.json`;
    anchor.click();
    URL.revokeObjectURL(href);
  }

  const selectedAssertion = selectedAssertionId
    ? (assertionLookup.get(selectedAssertionId) ?? null)
    : null;
  const selectedEntity = selectedEntityId ? (entityLookup.get(selectedEntityId) ?? null) : null;

  return (
    <div id="panel-graph" role="region" aria-label="Causal graph exploration">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <h2>Full evidence map</h2>
          <p className="section-note mt-2">Inspect entities, relationships, and their evidence.</p>
        </div>
        <div className="flex flex-wrap gap-3">
          <button type="button" className="text-link" onClick={fit}>
            Fit to view
          </button>
          <button type="button" className="text-link" onClick={exportVisible}>
            Export current view
          </button>
        </div>
      </div>
      <p className="section-note mt-4">
        Showing {visible.entities.length} of {result.graph.entities.length} nodes. Display changes
        do not rerun the investigation.
      </p>
      <div className="graph-workbench">
        <details className="graph-filters" open>
          <summary className="disclosure">Map controls</summary>
          <div className="graph-filter-fields">
            <label>
              <span className="mb-1 block text-sm">Search visible nodes</span>
              <span className="flex gap-2">
                <input
                  className="field min-w-0"
                  value={search}
                  onChange={(event) => setSearch(event.target.value)}
                  onKeyDown={(event) => event.key === "Enter" && findNode()}
                  placeholder="Entity name"
                />
                <button type="button" className="button-secondary px-3" onClick={findNode}>
                  Find
                </button>
              </span>
            </label>
            <label>
              <span className="mb-1 block text-sm">Highlight mechanism</span>
              <select
                className="field"
                value={pathId}
                onChange={(event) => {
                  setPathId(event.target.value);
                  setScope(initialGraphNodes(result, event.target.value));
                }}
              >
                <option value="all">No highlighted path</option>
                {result.hypotheses.map((hypothesis) => (
                  <option value={hypothesis.id} key={hypothesis.id}>
                    {hypothesis.title}
                  </option>
                ))}
              </select>
            </label>
            <GraphSelect
              label="Node type"
              value={entityType}
              onChange={setEntityType}
              options={options.entityTypes}
            />
            <GraphSelect
              label="Relation"
              value={relation}
              onChange={setRelation}
              options={options.relations}
            />
            <GraphSelect
              label="Evidence grade"
              value={grade}
              onChange={setGrade}
              options={["A", "B", "C", "D", "E", "U"]}
            />
            <GraphSelect
              label="Organism"
              value={organism}
              onChange={setOrganism}
              options={options.organisms}
            />
            <GraphSelect
              label="Tissue"
              value={tissue}
              onChange={setTissue}
              options={[
                ...new Set(
                  result.graph.assertions.flatMap((edge) =>
                    edge.biological_context.tissue ? [edge.biological_context.tissue] : [],
                  ),
                ),
              ]}
            />
            <GraphSelect
              label="Causal status"
              value={causalStatus}
              onChange={setCausalStatus}
              options={[...new Set(result.graph.assertions.map((edge) => edge.causal_status))]}
            />
            <GraphSelect
              label="Intervention class"
              value={interventionClass}
              onChange={setInterventionClass}
              options={[...new Set(result.interventions.map((item) => item.intervention_class))]}
            />
          </div>
          <div className="graph-scope-actions">
            <h3>Extend the map</h3>
            <button
              className="text-link"
              onClick={() => setScope((current) => expandGraphNodes(result, current, "upstream"))}
            >
              Expand upstream
            </button>
            <button
              className="text-link"
              onClick={() => setScope((current) => expandGraphNodes(result, current, "downstream"))}
            >
              Expand downstream
            </button>
            <button
              className="text-link"
              onClick={() =>
                setScope((current) =>
                  expandGraphNodes(
                    result,
                    expandGraphNodes(result, current, "upstream"),
                    "downstream",
                  ),
                )
              }
            >
              Expand neighbors
            </button>
            <button
              className="text-link"
              onClick={() =>
                setScope((current) => [
                  ...new Set([
                    ...current,
                    ...result.interventions.flatMap((item) => [
                      ...item.target_entity_ids,
                      ...result.graph.assertions
                        .filter((edge) => item.downstream_assertion_ids.includes(edge.id))
                        .flatMap((edge) => [edge.subject_id, edge.object_id]),
                    ]),
                  ]),
                ])
              }
            >
              Show interventions
            </button>
            <button
              className="text-link"
              onClick={() => revealTypes(["gene", "protein", "receptor", "enzyme"])}
            >
              Show genes/proteins
            </button>
            <button className="text-link" onClick={() => revealTypes(["cell_type"])}>
              Show cell types
            </button>
            <button
              className="text-link"
              onClick={() =>
                setScope((current) => [
                  ...new Set([
                    ...current,
                    ...result.hypotheses
                      .filter((item) => item.id !== pathId)
                      .flatMap((item) => item.mechanism_paths.flatMap((path) => path.entity_ids)),
                  ]),
                ])
              }
            >
              Show competing pathways
            </button>
            <button
              className="text-link"
              onClick={() => setScope(result.graph.entities.map((entity) => entity.id))}
            >
              Show full research graph
            </button>
            <button className="text-link" onClick={focusSelection} disabled={!selectedEntityId}>
              Focus selected branch
            </button>
            <button className="text-link" onClick={resetView}>
              Reset view
            </button>
          </div>
        </details>
        <div className="graph-canvas-region">
          {!visible.entities.length && (
            <p role="status" className="section-note py-4">
              No connections match these filters. Reset the view or expand the graph.
            </p>
          )}
          <div
            ref={containerRef}
            className="cytoscape-canvas"
            role="img"
            aria-label={`Interactive causal graph with ${visible.entities.length} entities and ${visible.assertions.length} assertions`}
            aria-describedby="graph-text-alternative"
          />
          <p id="graph-text-alternative" className="section-note mt-3">
            Zoom the map to read its labels, or use the text version below. Select a node or
            connection to inspect its evidence.
          </p>
          <div className="graph-legend" aria-label="Graph legend">
            <Legend line="solid" label="causal or mechanistic" />
            <Legend line="dashed" label="association" />
            <Legend line="dotted" label="predicted or hypothesis" />
            <Legend line="tee" label="inhibitory" />
            <span>Oxide line: conflicting evidence or a weak link</span>
            <span>Ochre outline: highlighted pathway</span>
            <span>Diamond: outcome / symptom</span>
            <span>Hexagon: behavior</span>
            <span>Rectangle: tissue / condition</span>
          </div>
          <details className="mt-5">
            <summary className="disclosure">Text version of visible map</summary>
            <ul className="mt-3 space-y-4">
              {visible.assertions.map((assertion) => (
                <li key={assertion.id}>
                  <button
                    className="text-link text-left"
                    onClick={() => {
                      setSelectedAssertionId(assertion.id);
                      setSelectedEntityId(null);
                    }}
                  >
                    {entityLookup.get(assertion.subject_id)?.preferred_name} →{" "}
                    {humanize(assertion.relation)} →{" "}
                    {entityLookup.get(assertion.object_id)?.preferred_name}
                  </button>
                  <p className="section-note mt-1">
                    {humanize(assertion.causal_status)} · Grade{" "}
                    {assertion.confidence_classification}
                    {assertion.polarity < 0 ? " · Inhibitory" : ""}
                    {assertion.contradictory_evidence_ids.length ? " · Conflicting evidence" : ""}
                  </p>
                </li>
              ))}
            </ul>
          </details>
          <button
            className="text-link mt-5"
            aria-expanded={studiesOpen}
            onClick={() => setStudiesOpen(!studiesOpen)}
          >
            Show supporting studies
          </button>
        </div>
        <aside className="graph-inspector" aria-label="Map inspector" aria-live="polite">
          <h3>Inspector</h3>
          <label className="mt-4 block">
            <span className="mb-1 block text-sm">Inspect a relationship</span>
            <select
              className="field"
              value={selectedAssertionId ?? ""}
              onChange={(event) => {
                setSelectedAssertionId(event.target.value || null);
                setSelectedEntityId(null);
              }}
            >
              <option value="">Choose a relationship</option>
              {visible.assertions.map((assertion) => (
                <option value={assertion.id} key={assertion.id}>
                  {entityLookup.get(assertion.subject_id)?.preferred_name} →{" "}
                  {humanize(assertion.relation)} →{" "}
                  {entityLookup.get(assertion.object_id)?.preferred_name}
                </option>
              ))}
            </select>
          </label>
          <div className="mt-5">
            {selectedAssertion ? (
              <EdgePanel
                assertion={selectedAssertion}
                entityLookup={entityLookup}
                evidenceLookup={evidenceLookup}
              />
            ) : selectedEntity ? (
              <NodePanel
                entity={selectedEntity}
                assertions={result.graph.assertions}
                entityLookup={entityLookup}
              />
            ) : (
              <p className="section-note">
                Choose a relationship above, or select a node or connection on the map, to inspect
                its context, sources, and limitations.
              </p>
            )}
          </div>
        </aside>
      </div>
      {studiesOpen && (
        <section className="mt-5 space-y-3">
          <h3 className="font-bold">Studies supporting visible connections</h3>
          {result.graph.evidence
            .filter((record) =>
              visible.assertions.some((edge) => edge.supporting_evidence_ids.includes(record.id)),
            )
            .map((record) => (
              <EvidenceCard key={record.id} record={record} />
            ))}
        </section>
      )}
      <div className="mt-4 flex flex-wrap gap-3 text-xs">
        <a
          className="font-bold text-[var(--accent)] hover:underline"
          href={`${API_URL}/api/v1/graph-exports/${result.id}/json-ld`}
        >
          Full JSON-LD ↓
        </a>
        <a
          className="font-bold text-[var(--accent)] hover:underline"
          href={`${API_URL}/api/v1/graph-exports/${result.id}/graphml`}
        >
          GraphML ↓
        </a>
        <a
          className="font-bold text-[var(--accent)] hover:underline"
          href={`${API_URL}/api/v1/graph-exports/${result.id}/nodes-csv`}
        >
          Nodes CSV ↓
        </a>
        <a
          className="font-bold text-[var(--accent)] hover:underline"
          href={`${API_URL}/api/v1/graph-exports/${result.id}/edges-csv`}
        >
          Edges CSV ↓
        </a>
      </div>
    </div>
  );
}

function GraphSelect({
  label,
  value,
  onChange,
  options,
}: {
  label: string;
  value: string;
  onChange: (value: string) => void;
  options: string[];
}) {
  return (
    <label>
      <span className="mb-1 block text-sm">{label}</span>
      <select className="field" value={value} onChange={(event) => onChange(event.target.value)}>
        <option value="all">All</option>
        {options.map((option) => (
          <option value={option} key={option}>
            {humanize(option)}
          </option>
        ))}
      </select>
    </label>
  );
}

function EdgePanel({
  assertion,
  entityLookup,
  evidenceLookup,
}: {
  assertion: CausalAssertion;
  entityLookup: Map<string, BiologicalEntity>;
  evidenceLookup: Map<string, EvidenceRecord>;
}) {
  const subject = entityLookup.get(assertion.subject_id);
  const object = entityLookup.get(assertion.object_id);
  const supporting = assertion.supporting_evidence_ids.flatMap(
    (id) => evidenceLookup.get(id) ?? [],
  );
  const contradictory = assertion.contradictory_evidence_ids.flatMap(
    (id) => evidenceLookup.get(id) ?? [],
  );
  return (
    <div>
      <p className="section-note">Relationship</p>
      <div className="section-note mt-3">
        Grade {assertion.confidence_classification} · {humanize(assertion.causal_status)}
        {contradictory.length ? (
          <span className="block mt-1 text-[var(--red)]">
            {contradictory.length} conflicting source{contradictory.length === 1 ? "" : "s"}
          </span>
        ) : null}
      </div>
      <h4 className="mt-4 text-base leading-6">
        {subject?.preferred_name} {humanize(assertion.relation).toLowerCase()}{" "}
        {object?.preferred_name}
      </h4>
      <p className="section-note mt-3">{assertion.interpretation}</p>
      <dl className="metadata mt-4">
        <dt className="font-bold">Species</dt>
        <dd className="text-[var(--ink-muted)]">{assertion.biological_context.species}</dd>
        <dt className="font-bold">Population</dt>
        <dd className="text-[var(--ink-muted)]">{assertion.biological_context.population}</dd>
        <dt className="font-bold">Tissue</dt>
        <dd className="text-[var(--ink-muted)]">
          {assertion.biological_context.tissue ?? "Not specified"}
        </dd>
        <dt className="font-bold">Review state</dt>
        <dd className="text-[var(--ink-muted)]">{assertion.review_status}</dd>
      </dl>
      <EvidenceLinks title="Supporting evidence" records={supporting} />
      {contradictory.length ? (
        <EvidenceLinks title="Contradictory evidence" records={contradictory} />
      ) : null}
      {assertion.limitations.length ? (
        <div className="mt-4">
          <h4>Limitations</h4>
          <ul className="section-note mt-2 list-disc space-y-1 pl-4">
            {assertion.limitations.map((item) => (
              <li key={item}>{item}</li>
            ))}
          </ul>
        </div>
      ) : null}
      <details className="mt-5">
        <summary className="disclosure">Identifiers and provenance</summary>
        <p className="mt-3 break-all font-mono text-xs leading-6 text-[var(--ink-muted)]">
          assertion_id={assertion.id}
          <br />
          subject={assertion.subject_id}
          <br />
          object={assertion.object_id}
          <br />
          source={assertion.source}
          <br />
          retrieved={assertion.retrieval_date}
        </p>
      </details>
    </div>
  );
}

function EvidenceLinks({ title, records }: { title: string; records: EvidenceRecord[] }) {
  return (
    <div className="mt-4">
      <h4>{title}</h4>
      <div className="mt-2 space-y-4">
        {records.map((record) => (
          <a
            key={record.id}
            href={record.study.source_url}
            target="_blank"
            rel="noreferrer"
            className="text-link block text-sm leading-6"
          >
            <span>{record.study.title}</span>
            <span className="section-note mt-1 block">
              {record.study.publication_year} · Grade {record.evidence_grade} ·{" "}
              {record.experimental_context.species}
            </span>
          </a>
        ))}
      </div>
    </div>
  );
}

function NodePanel({
  entity,
  assertions,
  entityLookup,
}: {
  entity: BiologicalEntity;
  assertions: CausalAssertion[];
  entityLookup: Map<string, BiologicalEntity>;
}) {
  const connected = assertions.filter(
    (item) => item.subject_id === entity.id || item.object_id === entity.id,
  );
  return (
    <div>
      <p className="section-note">{humanize(entity.entity_type)}</p>
      <h4 className="mt-3 text-lg">{entity.preferred_name}</h4>
      <p className="section-note mt-2">{entity.description}</p>
      {entity.aliases.length ? (
        <p className="section-note mt-3">
          <strong>Aliases:</strong> {entity.aliases.join(", ")}
        </p>
      ) : null}
      <h4 className="mt-5">Connected assertions ({connected.length})</h4>
      <ul className="section-note mt-2 max-h-56 space-y-3 overflow-y-auto">
        {connected.map((item) => (
          <li key={item.id}>
            {entityLookup.get(item.subject_id)?.preferred_name}{" "}
            {humanize(item.relation).toLowerCase()}{" "}
            {entityLookup.get(item.object_id)?.preferred_name}
          </li>
        ))}
      </ul>
      <details className="mt-5">
        <summary className="disclosure">Identifiers and provenance</summary>
        <p className="mt-3 break-all font-mono text-xs leading-6 text-[var(--ink-muted)]">
          entity_id={entity.id}
          <br />
          state={entity.curation_status}
          <br />
          source={entity.source}
        </p>
      </details>
    </div>
  );
}

function Legend({ line, label }: { line: "solid" | "dashed" | "dotted" | "tee"; label: string }) {
  const borderStyle = line === "tee" ? "solid" : line;
  return (
    <span className="inline-flex items-center gap-1.5">
      <span
        className="inline-block w-7 border-t border-[var(--ink-muted)]"
        style={{ borderTopStyle: borderStyle }}
      />
      {line === "tee" ? "⊣ " : ""}
      {label}
    </span>
  );
}
