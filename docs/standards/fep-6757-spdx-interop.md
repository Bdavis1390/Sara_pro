# FEP-6757 / SPDX interoperability note

Status: working standards note  
Branch: `standards/fep-6757-spdx`  
Purpose: preserve the current interoperability analysis for contribution to Fediverse licensing discussions.

## Executive position

Treat license identity, broader rights information, usage-policy semantics, AI/crawler preferences, and provenance as distinct layers.

- Use `dcterms:license` as the generic relation to the governing legal license/document.
- Use `dcterms:rights` for broader rights information.
- Permit SPDX License Expressions where precise machine-readable composition is needed.
- Keep ODRL orthogonal for permissions, prohibitions, duties, and constraints.
- Keep AI-training/search/crawler preferences outside copyright-license metadata.
- Preserve attribution, source, and relevant provenance across federation and transformations.

This avoids both extremes: requiring the full SPDX object model for ordinary ActivityPub objects, or discouraging SPDX even where its expression grammar adds real interoperability value.

## Why SPDX still matters

A set of license IRIs is insufficient to preserve composition semantics. It does not, by itself, distinguish:

- `MIT OR Apache-2.0`
- `MIT AND Apache-2.0`
- `GPL-2.0-or-later WITH Bison-exception-2.2`
- custom `LicenseRef-*` identifiers

SPDX License Expressions already provide a standardized grammar for these cases.

The FEP should reference the SPDX expression grammar rather than freeze Fediverse interoperability to a specific SPDX RDF object model/version.

## Scope rule

A licensing assertion applies only to the ActivityStreams Object on which the assertion occurs.

A parent Note MUST NOT silently relicense its attachments.

Absence of licensing metadata means only:

> no licensing assertion was supplied for this object

It MUST NOT be interpreted as:

- inherited license,
- public domain,
- all rights reserved,
- permission to scrape/train/index,
- permission to redistribute.

## Layered model

```text
ActivityStreams Object
  |
  +-- dcterms:license -------> governing license / legal document
  |
  +-- dcterms:rights --------> broader rights statement
  |
  +-- SPDX expression -------> exact license composition when needed
  |
  +-- ODRL policy -----------> permissions / prohibitions / duties / constraints
  |
  +-- AI preference ---------> separate processing preference signal
  |
  +-- provenance -----------> attribution / source / transformation history
```

## Candidate wire profile

Simple case:

```json
{
  "@context": [
    "https://www.w3.org/ns/activitystreams",
    {
      "license": {
        "@id": "http://purl.org/dc/terms/license",
        "@type": "@id"
      },
      "rights": {
        "@id": "http://purl.org/dc/terms/rights",
        "@type": "@id"
      }
    }
  ],
  "type": "Image",
  "license": "https://creativecommons.org/licenses/by/4.0/"
}
```

Compound-license case:

```json
{
  "@context": [
    "https://www.w3.org/ns/activitystreams",
    {
      "license": {
        "@id": "http://purl.org/dc/terms/license",
        "@type": "@id"
      },
      "rights": {
        "@id": "http://purl.org/dc/terms/rights",
        "@type": "@id"
      },
      "licenseExpression": "https://w3id.org/fep/6757#licenseExpression"
    }
  ],
  "type": "Document",
  "licenseExpression": "MIT OR Apache-2.0"
}
```

If a FEP-specific `licenseExpression` property is retained, its value should be normatively defined as a valid SPDX License Expression and should not become a competing license grammar.

## Mixed-license attachment example

```json
{
  "@context": [
    "https://www.w3.org/ns/activitystreams",
    {
      "license": {
        "@id": "http://purl.org/dc/terms/license",
        "@type": "@id"
      },
      "licenseExpression": "https://w3id.org/fep/6757#licenseExpression"
    }
  ],
  "type": "Note",
  "content": "Post body",
  "license": "https://creativecommons.org/licenses/by-sa/4.0/",
  "attachment": [
    {
      "type": "Image",
      "url": "https://example.org/a.jpg",
      "license": "https://creativecommons.org/publicdomain/zero/1.0/"
    },
    {
      "type": "Document",
      "url": "https://example.org/b.txt",
      "licenseExpression": "MIT OR Apache-2.0"
    },
    {
      "type": "Image",
      "url": "https://example.org/c.jpg"
    }
  ]
}
```

The third attachment has no licensing assertion. The Note's license does not automatically apply to it.

## Manyfold compatibility

Manyfold has deployed ActivityPub licensing metadata using SPDX-oriented terms, including `LicenseRef-*` for non-listed licenses.

A migration path should therefore:

1. accept the existing Manyfold representation when it can be translated unambiguously;
2. preserve unknown/custom identifiers rather than silently discarding them;
3. transmit the standardized FEP profile going forward;
4. avoid binding the FEP to the older SPDX RDF namespace.

## Custom license references

A `LicenseRef-*` identifier should be accompanied by enough information for a receiver to recover its meaning.

Recommended supporting data may include:

- a stable license URI,
- supplied license text,
- an integrity hash,
- provenance for who supplied the custom definition.

## Transformations and provenance

Federated software routinely resizes images, transcodes video, strips metadata, creates previews, caches remote media, or otherwise transforms representations.

Implementations SHOULD preserve:

- the licensing assertion associated with the source,
- attribution,
- original-source identifiers,
- enough transformation history to distinguish original and derived representations.

An integrity proof may authenticate who made an assertion and whether it was modified in transit. It does not prove that the asserting actor owns the copyright or otherwise has authority to grant the asserted rights.

## Conformance vectors

| Case | Expected result |
|---|---|
| `CC-BY-4.0` | accept as valid SPDX expression |
| `MIT OR Apache-2.0` | accept and preserve OR semantics |
| `GPL-2.0-or-later WITH Bison-exception-2.2` | accept |
| `(MIT OR Apache-2.0) AND BSD-3-Clause` | accept and preserve grouping |
| `LicenseRef-Example` | accept as custom reference; supporting definition recommended |
| invalid expression | do not infer a license; do not reject the whole ActivityPub object |
| unknown/new SPDX identifier | preserve value; mark unrecognized if necessary |
| missing license metadata | no assertion |
| licensed Note + differently licensed attachment | preserve independent scopes |
| licensed Note + unlicensed attachment | do not inherit automatically |
| Announce of a licensed object | announcer does not replace origin's license assertion |
| Update changing licensing metadata | update current assertion; retain prior provenance where available |

## AI/search/indexing preferences

Do not overload licensing fields with AI-training, crawler, search, or indexing preferences.

Those concerns belong in a distinct preference/policy mechanism. A license may have legal consequences, but a processing preference is not automatically a copyright license and vice versa.

## Ready-to-post issue comment

The following text is suitable for the current FEP discussion:

> I think the proposal becomes considerably simpler if it separates license metadata from usage preferences.
>
> `dcterms:license` should remain the generic relation for identifying the legal license governing a resource, while `dcterms:rights` can carry broader rights information. SPDX should not replace those properties.
>
> However, SPDX License Expressions solve a distinct interoperability problem: they preserve composition semantics that a set of license URIs cannot express, including `AND`, `OR`, `WITH`, custom `LicenseRef-*` references, and parentheses.
>
> I therefore suggest that the FEP permit an optional license-expression value whose syntax is normatively the SPDX License Expression grammar. This should be an adjunct to, not a replacement for, `dcterms:license`.
>
> The assertion should apply only to the ActivityStreams Object on which it occurs. It MUST NOT silently propagate to attachments. Absence of licensing metadata should mean "no assertion supplied."
>
> AI-training, AI-use, search, and crawler preferences should remain outside this licensing mechanism.
>
> Finally, I would avoid coupling the FEP to a particular SPDX RDF-version structure. The expression grammar is the more stable interoperability boundary.
>
> A receiver SHOULD preserve an expression it cannot fully interpret rather than discarding the entire ActivityPub object, and implementations SHOULD preserve licensing, attribution, source, and relevant provenance across federation and transformations.
>
> Existing implementations such as Manyfold's SPDX-oriented ActivityPub representation should have a documented compatibility path where conversion is unambiguous.

## References

- SPDX 3.0.1 License Expressions: https://spdx.github.io/spdx-spec/v3.0.1/annexes/spdx-license-expressions/
- DCMI `license`: https://www.dublincore.org/specifications/dublin-core/dcmi-terms/terms/license/
- W3C ODRL 2.2 Information Model: https://www.w3.org/TR/odrl-model/
- FEP-c118: https://fediverse.codeberg.page/fep/fep/c118/
- SocialHub FEP-c118 discussion: https://socialhub.activitypub.rocks/t/fep-c118-content-licensing-support/2903
- Manyfold ActivityPub documentation: https://manyfold.app/technology/activitypub.html
- W3C ActivityStreams issue #787: https://github.com/w3c/activitystreams/issues/787
