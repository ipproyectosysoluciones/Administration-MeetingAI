// Minutes domain types (re-exported from the canonical definitions in src/lib/minutes.ts)
import type { Minute, MinuteListResponse, MinuteCreatePayload } from '@/lib/minutes';

export type MinuteResponse = Minute;
export type { MinuteListResponse };
export type MinuteCreateRequest = MinuteCreatePayload;
export type MinuteUpdateRequest = Partial<Pick<Minute, 'title' | 'content'>>;

export interface MinuteVersionResponse {
  id: string;
  minute_id: string;
  version: number;
  content: string;
  change_summary: string | null;
  created_by: string;
  created_at: string;
}

export interface MinuteVersionListResponse {
  items: MinuteVersionResponse[];
  total: number;
  page: number;
  page_size: number;
  pages: number;
}
