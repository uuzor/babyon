"use client";

import { useEffect, useState } from "react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { api, BlockchainOverview } from "@/lib/api";
import { formatNumber } from "@/lib/utils";
import { Activity, Users, ArrowUpRight, Clock, Layers } from "lucide-react";

export default function BlockchainPage() {
  const [overview, setOverview] = useState<BlockchainOverview | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function fetchData() {
      try {
        setLoading(true);
        const data = await api.getBlockchainOverview();
        setOverview(data);
        setError(null);
      } catch (err) {
        setError(err instanceof Error ? err.message : "Failed to fetch data");
      } finally {
        setLoading(false);
      }
    }

    fetchData();
    const interval = setInterval(fetchData, 10000);
    return () => clearInterval(interval);
  }, []);

  if (loading) {
    return (
      <div className="space-y-6">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Blockchain Metrics</h1>
          <p className="text-muted-foreground">Loading...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="space-y-6">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Blockchain Metrics</h1>
          <p className="text-muted-foreground">Detailed blockchain statistics</p>
        </div>
        <Card className="border-destructive">
          <CardHeader>
            <CardTitle>Error Loading Data</CardTitle>
            <CardDescription>{error}</CardDescription>
          </CardHeader>
        </Card>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Blockchain Metrics</h1>
          <p className="text-muted-foreground">
            Detailed blockchain statistics and network health
          </p>
        </div>
        <Badge variant="success" className="text-xs">
          <Clock className="w-3 h-3 mr-1" />
          Real-time
        </Badge>
      </div>

      {/* Key Metrics */}
      <div className="grid gap-4 md:grid-cols-3">
        <Card className="border-2">
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Current Block Height</CardTitle>
            <Layers className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-3xl font-bold">
              {formatNumber(overview?.latest_block || 0)}
            </div>
            <p className="text-xs text-muted-foreground mt-2">
              Latest synchronized block
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Total Transactions</CardTitle>
            <Activity className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-3xl font-bold">
              {formatNumber(overview?.total_transactions || 0)}
            </div>
            <p className="text-xs text-muted-foreground mt-2">
              All-time transaction count
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Active Addresses</CardTitle>
            <Users className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-3xl font-bold">
              {formatNumber(overview?.total_addresses || 0)}
            </div>
            <p className="text-xs text-muted-foreground mt-2">
              Unique wallet addresses
            </p>
          </CardContent>
        </Card>
      </div>

      {/* Network Activity */}
      <div className="grid gap-4 md:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle>Network Activity</CardTitle>
            <CardDescription>Transaction throughput metrics</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="flex justify-between items-center">
              <span className="text-sm text-muted-foreground">Avg TX per Block</span>
              <span className="text-lg font-semibold">
                {overview?.avg_transactions_per_block?.toFixed(2) || "0.00"}
              </span>
            </div>
            <div className="flex justify-between items-center">
              <span className="text-sm text-muted-foreground">Total Transfers</span>
              <span className="text-lg font-semibold">
                {formatNumber(overview?.total_transfers || 0)}
              </span>
            </div>
            <div className="flex justify-between items-center">
              <span className="text-sm text-muted-foreground">TX/Transfer Ratio</span>
              <span className="text-lg font-semibold">
                {overview?.total_transactions && overview?.total_transfers
                  ? (overview.total_transactions / overview.total_transfers).toFixed(2)
                  : "0.00"}
              </span>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Data Synchronization</CardTitle>
            <CardDescription>Indexer and database status</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div>
              <div className="flex items-center justify-between mb-1">
                <span className="text-sm text-muted-foreground">Last Update</span>
                <Badge variant="outline" className="text-xs">
                  {overview?.last_updated
                    ? new Date(overview.last_updated).toLocaleTimeString()
                    : "N/A"}
                </Badge>
              </div>
            </div>
            <div>
              <div className="flex items-center justify-between mb-1">
                <span className="text-sm text-muted-foreground">Data Source</span>
                <Badge variant="secondary" className="text-xs">
                  Babylon Testnet
                </Badge>
              </div>
            </div>
            <div>
              <div className="flex items-center justify-between mb-1">
                <span className="text-sm text-muted-foreground">Refresh Rate</span>
                <Badge variant="outline" className="text-xs">
                  10 seconds
                </Badge>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Network Stats Grid */}
      <Card>
        <CardHeader>
          <CardTitle>Network Statistics</CardTitle>
          <CardDescription>Comprehensive blockchain data overview</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <div className="p-4 border rounded-lg">
              <div className="text-sm text-muted-foreground mb-1">Blocks</div>
              <div className="text-2xl font-bold">{formatNumber(overview?.latest_block || 0)}</div>
            </div>
            <div className="p-4 border rounded-lg">
              <div className="text-sm text-muted-foreground mb-1">Transactions</div>
              <div className="text-2xl font-bold">{formatNumber(overview?.total_transactions || 0)}</div>
            </div>
            <div className="p-4 border rounded-lg">
              <div className="text-sm text-muted-foreground mb-1">Addresses</div>
              <div className="text-2xl font-bold">{formatNumber(overview?.total_addresses || 0)}</div>
            </div>
            <div className="p-4 border rounded-lg">
              <div className="text-sm text-muted-foreground mb-1">Transfers</div>
              <div className="text-2xl font-bold">{formatNumber(overview?.total_transfers || 0)}</div>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Additional Information */}
      <Card>
        <CardHeader>
          <CardTitle>About Babylon Genesis Chain</CardTitle>
          <CardDescription>Network information and documentation</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="space-y-3 text-sm text-muted-foreground">
            <p>
              Babylon Genesis Chain is a Cosmos SDK-based Layer 1 blockchain with over $4B TVL.
              It features dual-quorum staking and innovative Bitcoin finality providers.
            </p>
            <div className="flex gap-4 mt-4">
              <a
                href="https://babylonlabs.io"
                target="_blank"
                rel="noopener noreferrer"
                className="flex items-center text-primary hover:underline"
              >
                Official Website
                <ArrowUpRight className="w-3 h-3 ml-1" />
              </a>
              <a
                href="https://docs.babylonlabs.io"
                target="_blank"
                rel="noopener noreferrer"
                className="flex items-center text-primary hover:underline"
              >
                Documentation
                <ArrowUpRight className="w-3 h-3 ml-1" />
              </a>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
