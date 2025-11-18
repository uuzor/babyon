"use client";

import { useEffect, useState } from "react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { api, BlockchainOverview } from "@/lib/api";
import { formatNumber } from "@/lib/utils";
import { Activity, TrendingUp, Users, ArrowUpRight } from "lucide-react";

export default function DashboardPage() {
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
    // Refresh every 30 seconds
    const interval = setInterval(fetchData, 30000);
    return () => clearInterval(interval);
  }, []);

  if (loading) {
    return (
      <div className="space-y-6">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Dashboard</h1>
          <p className="text-muted-foreground">
            Loading blockchain analytics...
          </p>
        </div>
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
          {[...Array(4)].map((_, i) => (
            <Card key={i} className="animate-pulse">
              <CardHeader className="pb-2">
                <div className="h-4 bg-muted rounded w-1/2" />
              </CardHeader>
              <CardContent>
                <div className="h-8 bg-muted rounded w-3/4" />
              </CardContent>
            </Card>
          ))}
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="space-y-6">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Dashboard</h1>
          <p className="text-muted-foreground">
            Real-time blockchain analytics for Babylon Genesis Chain
          </p>
        </div>
        <Card className="border-destructive">
          <CardHeader>
            <CardTitle>Error Loading Data</CardTitle>
            <CardDescription>{error}</CardDescription>
          </CardHeader>
          <CardContent>
            <p className="text-sm text-muted-foreground">
              Make sure the backend API is running at {process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'}
            </p>
          </CardContent>
        </Card>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Dashboard</h1>
          <p className="text-muted-foreground">
            Real-time blockchain analytics for Babylon Genesis Chain
          </p>
        </div>
        <Badge variant="success" className="text-xs">
          Live
        </Badge>
      </div>

      {/* Stats Grid */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        {/* Latest Block */}
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Latest Block</CardTitle>
            <Activity className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {formatNumber(overview?.latest_block || 0)}
            </div>
            <p className="text-xs text-muted-foreground mt-1">
              Current blockchain height
            </p>
          </CardContent>
        </Card>

        {/* Total Transactions */}
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Transactions</CardTitle>
            <TrendingUp className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {formatNumber(overview?.total_transactions || 0)}
            </div>
            <p className="text-xs text-muted-foreground mt-1">
              Total on-chain transactions
            </p>
          </CardContent>
        </Card>

        {/* Total Addresses */}
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Addresses</CardTitle>
            <Users className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {formatNumber(overview?.total_addresses || 0)}
            </div>
            <p className="text-xs text-muted-foreground mt-1">
              Unique active addresses
            </p>
          </CardContent>
        </Card>

        {/* Total Transfers */}
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Transfers</CardTitle>
            <ArrowUpRight className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {formatNumber(overview?.total_transfers || 0)}
            </div>
            <p className="text-xs text-muted-foreground mt-1">
              Total token transfers
            </p>
          </CardContent>
        </Card>
      </div>

      {/* Additional Info */}
      <div className="grid gap-4 md:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle>Network Activity</CardTitle>
            <CardDescription>Average transactions per block</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="text-3xl font-bold">
              {overview?.avg_transactions_per_block?.toFixed(2) || "0.00"}
            </div>
            <p className="text-xs text-muted-foreground mt-2">
              Transactions per block (average)
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Last Updated</CardTitle>
            <CardDescription>Data synchronization status</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="text-sm">
              {overview?.last_updated
                ? new Date(overview.last_updated).toLocaleString()
                : "Not available"}
            </div>
            <p className="text-xs text-muted-foreground mt-2">
              Data refreshes every 30 seconds
            </p>
          </CardContent>
        </Card>
      </div>

      {/* Quick Links */}
      <Card>
        <CardHeader>
          <CardTitle>Quick Links</CardTitle>
          <CardDescription>Navigate to key analytics pages</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="grid gap-2">
            <a
              href="/smart-money"
              className="flex items-center justify-between p-3 rounded-md border hover:bg-accent transition-colors"
            >
              <div>
                <div className="font-medium">Smart Money Leaderboard</div>
                <div className="text-sm text-muted-foreground">
                  Top performing addresses ranked by smart money score
                </div>
              </div>
              <ArrowUpRight className="h-4 w-4 text-muted-foreground" />
            </a>
            <a
              href="/address"
              className="flex items-center justify-between p-3 rounded-md border hover:bg-accent transition-colors"
            >
              <div>
                <div className="font-medium">Address Lookup</div>
                <div className="text-sm text-muted-foreground">
                  Search and analyze any Babylon address
                </div>
              </div>
              <ArrowUpRight className="h-4 w-4 text-muted-foreground" />
            </a>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
