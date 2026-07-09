# Concept Dictionary (Lightweight Ontology)

> Plain-language glossary of the **concepts** in the sales domain, with the
> real-world definition, how each maps from the two sources, and the rule that
> governs it. This is the "ontology for humans" companion to
> [sales-ontology.ttl](sales-ontology.ttl).

A **concept** is a thing the business cares about, independent of how any system
stores it. The same concept can arrive as a CSV column *or* an XML element — the
ontology says they mean the same thing.

## Classes (the nouns)

| Concept | Definition (what it *means*) | Super-concept |
|---|---|---|
| **Party** | Any entity that can take part in a transaction | — |
| **Customer** | A Party that buys goods | Party |
| **Product** | A distinct item that can be sold | — |
| **Category** | A grouping of Products | — |
| **Sale** | An economic event: goods exchanged for money on a date | — |
| **Order** | A Sale captured by the e-commerce (CSV) system | Sale |
| **Invoice** | A Sale captured by the invoicing (SOAP/XML) system | Sale |
| **LineItem** | One product-quantity-price line within a Sale | — |

Key axiom: **`Order ⊑ Sale` and `Invoice ⊑ Sale`** (both *are* Sales). This is
the semantic reason `silver/sales` can hold both and gold can total them together.

## Relationships (the verbs / object properties)

| Relationship | From → To | Meaning | Cardinality |
|---|---|---|---|
| `placedBy` | Sale → Customer | who made the sale | exactly 1 |
| `hasLineItem` | Sale → LineItem | the lines that compose the sale | 1..many |
| `refersToProduct` | LineItem → Product | what was sold on the line | exactly 1 |
| `belongsToCategory` | Product → Category | how the product is grouped | exactly 1 |

## Attributes (data properties) and their source mappings

This table is the heart of the ontology: **one concept property, two source
expressions.** It mirrors the adapters in `src/silver.py`.

| Concept.property | Meaning | From ORDERS (CSV field) | From INVOICING (XML) | Rule / normalization |
|---|---|---|---|---|
| `Sale.sourceSystem` | which system observed the sale | literal `"orders"` | literal `"invoicing"` | provenance tag |
| `Sale.sourceId` | natural key within its source | `order_id` | `Invoice/@id` + `#<line ordinal>` | uppercased, must be non-empty |
| `Sale.occurredOn` | date the sale happened | `order_date` | `Invoice/@issued` | multi-format → `YYYY-MM-DD`; must parse |
| `Customer.id` | customer identity | `customer_id` | `Customer/@code` | uppercased |
| `Customer.name` | customer display name | `customer_name` | `Customer` text node | title-cased |
| `Product.name` | product identity | `product` | `Line/@product` | title-cased |
| `Category.name` | product grouping | `category` | `Line/@category` | title-cased; blank → `"Unknown"` |
| `LineItem.quantity` | units sold | `quantity` | `Line/Qty` | integer, **must be > 0** |
| `LineItem.unitPrice` | price per unit | `unit_price` | `Line/Amount` | strip `$`/`,`; **must be ≥ 0** |
| `Sale.revenue` | money for the line | *derived* | *derived* | `quantity × unitPrice`, rounded 2dp |

> Notice the last row: `revenue` is **not** stored by either source — it is
> *entailed* by the ontology rule. That is a tiny taste of inference.

## Axioms = your silver validation rules, restated

The rules the class already saw as "silver validation" are really **ontology
axioms** — statements that must hold for an instance to be a valid member of a
class:

| Axiom (ontology language) | Silver rule (code) | Reject reason if violated |
|---|---|---|
| every `Sale` has a non-empty `sourceId` | `source_id` present | `missing source_id` |
| every `Sale` has a parseable `occurredOn` | date parses | `unparseable date` |
| every `LineItem.quantity` is a positive integer | `quantity > 0` | `quantity not a positive integer` |
| every `LineItem.unitPrice` is a non-negative number | `unit_price >= 0` | `unit_price not a valid non-negative number` |
| a `Sale` is identified by (`sourceSystem`, `sourceId`) | dedupe key | (duplicate collapsed, latest wins) |

Instances that break an axiom don't vanish — they go to `silver/_quarantine`,
tagged with the reason. **Quarantine = "known instances that fail the ontology."**

## The teaching takeaway

- **Schema** = shape of storage. **Ontology** = shape of meaning.
- The two sources have *different schemas* but map to the *same concepts*.
- Data quality is just **conformance to the ontology's axioms**.
- A third source (say JSON) would only need a new mapping column here — no change
  to the concepts, and no change to gold.

---

**Contact:** George Gergues
