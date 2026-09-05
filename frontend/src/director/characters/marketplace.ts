/** Reserved Community / Marketplace fields. No storefront in this phase. */
export interface CommunityListingStub {
  characterId: string;
  listed: boolean;
  visibility: 'private' | 'unlisted' | 'public';
  price: number | null;
}

export const MARKETPLACE_ROUTE = '/director/marketplace';
