const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export interface BlockchainOverview {
  latest_block: number;
  total_transactions: number;
  total_addresses: number;
  total_transfers: number;
  avg_transactions_per_block: number;
  last_updated: string;
}

export interface SmartMoneyScore {
  address: string;
  score: number;
  rating: string;
  profitability_score: number;
  early_adoption_score: number;
  volume_score: number;
  win_rate_score: number;
  influence_score: number;
  last_updated: string;
}

export interface AddressInfo {
  address: string;
  labels: string[];
  first_seen: string | null;
  last_seen: string | null;
  transaction_count: number;
  total_volume: number;
  labels_confidence: Record<string, number>;
}

export interface Holding {
  denom: string;
  amount: string;
  value_usd?: number;
}

async function fetchAPI<T>(endpoint: string): Promise<T> {
  const response = await fetch(`${API_URL}${endpoint}`);

  if (!response.ok) {
    throw new Error(`API Error: ${response.status} ${response.statusText}`);
  }

  return response.json();
}

export const api = {
  // Blockchain endpoints
  async getBlockchainOverview(): Promise<BlockchainOverview> {
    return fetchAPI<BlockchainOverview>('/blockchain/overview');
  },

  // Smart Money endpoints
  async getSmartMoneyScore(address: string): Promise<SmartMoneyScore> {
    return fetchAPI<SmartMoneyScore>(`/smart-money/${address}`);
  },

  async getTopSmartMoney(limit: number = 50): Promise<SmartMoneyScore[]> {
    return fetchAPI<SmartMoneyScore[]>(`/smart-money/top?limit=${limit}`);
  },

  // Address endpoints
  async getAddressInfo(address: string): Promise<AddressInfo> {
    return fetchAPI<AddressInfo>(`/addresses/${address}`);
  },

  async getAddressHoldings(address: string): Promise<Record<string, Holding>> {
    return fetchAPI<Record<string, Holding>>(`/addresses/${address}/holdings`);
  },

  // Metrics endpoints
  async getTransactionMetrics(fromDate?: string, toDate?: string) {
    let endpoint = '/metrics/transactions';
    const params = new URLSearchParams();
    if (fromDate) params.append('from_date', fromDate);
    if (toDate) params.append('to_date', toDate);
    const query = params.toString();
    if (query) endpoint += `?${query}`;
    return fetchAPI(endpoint);
  },

  async getActiveAddresses(fromDate?: string, toDate?: string) {
    let endpoint = '/metrics/addresses';
    const params = new URLSearchParams();
    if (fromDate) params.append('from_date', fromDate);
    if (toDate) params.append('to_date', toDate);
    const query = params.toString();
    if (query) endpoint += `?${query}`;
    return fetchAPI(endpoint);
  },
};
