/**
 * Donation editor v1.1 types (UI-5).
 *
 * Single source of truth = the backend, surfaced through GENERATED types (no hand-maintained drift):
 *   - request/response *envelopes* come from the OpenAPI schema (`openapi.gen.ts`, via `openapi-typescript`)
 *   - the donation contract/phrasing *bodies* come from the two v1.1 JSON Schemas (`*.gen.ts`, via
 *     `json-schema-to-typescript`) — the backend keeps the body a passthrough dict, so these schemas are the
 *     only authority for its shape.
 *
 * Regenerate with `npm run gen:api-types` after a backend contract/endpoint change. Do not hand-edit the
 * `*.gen.ts` files; add convenience aliases HERE.
 */

import type { components } from './openapi.gen';
import type { IreneIntentDonationLanguageNeutralContractV11 } from './donation-contract.gen';
import type { IreneIntentDonationPerLanguagePhrasingV11 } from './donation-language.gen';

type Schemas = components['schemas'];

// ----- bodies (from the v1.1 JSON Schemas) -----

/** The language-neutral contract: methods + ParameterSpec core (name/type/required/canonical choices/min-max/
 *  entity_type) + per-method room_context. */
export type DonationContract = IreneIntentDonationLanguageNeutralContractV11;

/** Per-language phrasing: phrases/lemmas/patterns/examples + per-param extraction/aliases/choice_surfaces. */
export type DonationPhrasing = IreneIntentDonationPerLanguagePhrasingV11;

// ----- contract get/put envelopes (from OpenAPI) -----

export type DonationContractResponse = Schemas['DonationContractResponse'];
export type DonationContractUpdateResponse = Schemas['DonationContractUpdateResponse'];

// ----- QUAL-42: contract↔code wiring report -----

export type ContractWiringReport = Schemas['ContractWiringReportSchema'];
export type ContractValidationResponse = Schemas['ContractValidationResponse'];

// ----- QUAL-42: LLM translation validation + service -----

export type TranslationIssue = Schemas['TranslationIssueSchema'];
export type TranslationValidationRequest = Schemas['TranslationValidationRequest'];
export type TranslationValidationResponse = Schemas['TranslationValidationResponse'];

export type TranslatedMethod = Schemas['TranslatedMethodSchema'];
export type TranslateRequest = Schemas['TranslateRequest'];
export type TranslateResponse = Schemas['TranslateResponse'];
