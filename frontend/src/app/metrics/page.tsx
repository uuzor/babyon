"use client";

import { useEffect, useState } from "react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { api } from "@/lib/api";
import { formatNumber } from "@/lib/utils";
import { BarChart3, Activity, Users, TrendingUp, Clock } from "lucide-react";

interface MetricsData {
  total_transactions?: number;
  avg_per_day?: number;
  max_in_day?: number;
  total_active?: number;
  new_addresses?: number;
}

export default function MetricsPage() {
  const [txMetrics, setTxMetrics] = useState<MetricsData | null>(null);
  const [addressMetrics, setAddressMetrics] = useState<MetricsData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function fetchData() {
      try {
        setLoading(true);
        const now = new Date();
        const weekAgo = new Date(now.getTime() - 7 * 24 * 60 * 60 * 1000);

        const [tx, addr] = await Promise.allSettled([
          api.getTransactionMetrics(weekAgo.toISOString(), now.toISOString()),
          api.getActiveAddresses(weekAgo.toISOString(), now.toISOString()),
        ]);

        if (tx.status === "fulfilled") setTxMetrics(tx.value as MetricsData);
        if (addr.status === "fulfilled") setAddressMetrics(addr.value as MetricsData);

        if (tx.status === "rejected" && addr.status === "rejected") {
          setError("Failed to fetch metrics data");
        } else {
          setError(null);
        }
      } catch (err) {
        setError(err instanceof Error ? err.message : "Failed to fetch metrics");
      } finally {
        setLoading(false);
      }
    }

    fetchData();
    const interval = setInterval(fetchData, 60000);
    return () => clearInterval(interval);
  }, []);

  if (loading) {
    return (
      <div className="space-y-6">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Network Metrics</h1>
          <p className="text-muted-foreground">Loading...</p>
        </div>
      </div>
    );
  }

  if (error && !txMetrics && !addressMetrics) {
    return (
      <div className="space-y-6">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Network Metrics</h1>
          <p className="text-muted-foreground">Detailed network analytics</p>
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
          <h1 className="text-3xl font-bold tracking-tight">Network Metrics</h1>
          <p className="text-muted-foreground">
            Comprehensive network analytics and trends
          </p>
        </div>
        <Badge variant="secondary" className="text-xs">
          <Clock className="w-3 h-3 mr-1" />
          Last 7 Days
        </Badge>
      </div>

      {/* Transaction Metrics */}
      {txMetrics && (
        <div className="space-y-4">
          <h2 className="text-2xl font-semibold">Transaction Activity</h2>
          <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
            <Card>
              <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                <CardTitle className="text-sm font-medium">Total Transactions</CardTitle>
                <Activity className="h-4 w-4 text-muted-foreground" />
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold">
                  {formatNumber(txMetrics.total_transactions || 0)}
                </div>
                <p className="text-xs text-muted-foreground mt-1">
                  All transactions in period
                </p>
              </CardContent>
            </Card>

            <Card>
              <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                <CardTitle className="text-sm font-medium">Daily Average</CardTitle>
                <BarChart3 className="h-4 w-4 text-muted-foreground" />
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold">
                  {formatNumber(txMetrics.avg_per_day || 0)}
                </div>
                <p className="text-xs text-muted-foreground mt-1">
                  Transactions per day
                </p>
              </CardContent>
            </Card>

            <Card>
              <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                <CardTitle className="text-sm font-medium">Peak Day</CardTitle>
                <TrendingUp className="h-4 w-4 text-muted-foreground" />
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold">
                  {formatNumber(txMetrics.max_in_day || 0)}
                </div>
                <p className="text-xs text-muted-foreground mt-1">
                  Highest daily volume
                </p>
              </CardContent>
            </Card>
          </div>
        </div>
      )}

      {/* Address Metrics */}
      {addressMetrics && (
        <div className="space-y-4">
          <h2 className="text-2xl font-semibold">Address Activity</h2>
          <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
            <Card>
              <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                <CardTitle className="text-sm font-medium">Active Addresses</CardTitle>
                <Users className="h-4 w-4 text-muted-foreground" />
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold">
                  {formatNumber(addressMetrics.total_active || 0)}
                </div>
                <p className="text-xs text-muted-foreground mt-1">
                  Addresses with activity
                </p>
              </CardContent>
            </Card>

            <Card>
              <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                <CardTitle className="text-sm font-medium">New Addresses</CardTitle>
                <Users className="h-4 w-4 text-muted-foreground" />
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold">
                  {formatNumber(addressMetrics.new_addresses || 0)}
                </div>
                <p className="text-xs text-muted-foreground mt-1">
                  First-time addresses
                </p>
              </CardContent>
            </Card>

            <Card>
              <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                <CardTitle className="text-sm font-medium">Daily Average</CardTitle>
                <BarChart3 className="h-4 w-4 text-muted-foreground" />
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold">
                  {formatNumber(addressMetrics.avg_per_day || 0)}
                </div>
                <p className="text-xs text-muted-foreground mt-1">
                  Active addresses per day
                </p>
              </CardContent>
            </Card>
          </div>
        </div>
      )}

      {/* Network Health */}
      <Card>
        <CardHeader>
          <CardTitle>Network Health Indicators</CardTitle>
          <CardDescription>Key metrics for network activity and growth</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            {txMetrics && (
              <div className="flex items-center justify-between p-4 border rounded-lg">
                <div>
                  <div className="font-medium">Transaction Activity</div>
                  <div className="text-sm text-muted-foreground">
                    Average daily transactions over the last week
                  </div>
                </div>
                <Badge variant="success" className="text-lg px-4 py-2">
                  {formatNumber(txMetrics.avg_per_day || 0)}
                </Badge>
              </div>
            )}

            {addressMetrics && (
              <div className="flex items-center justify-between p-4 border rounded-lg">
                <div>
                  <div className="font-medium">Address Growth</div>
                  <div className="text-sm text-muted-foreground">
                    New unique addresses joining the network
                  </div>
                </div>
                <Badge variant="success" className="text-lg px-4 py-2">
                  +{formatNumber(addressMetrics.new_addresses || 0)}
                </Badge>
              </div>
            )}

            {txMetrics && addressMetrics && (
              <div className="flex items-center justify-between p-4 border rounded-lg">
                <div>
                  <div className="font-medium">Engagement Rate</div>
                  <div className="text-sm text-muted-foreground">
                    Average transactions per active address
                  </div>
                </div>
                <Badge variant="outline" className="text-lg px-4 py-2">
                  {(
                    (txMetrics.total_transactions || 0) /
                    (addressMetrics.total_active || 1)
                  ).toFixed(2)}
                </Badge>
              </div>
            )}
          </div>
        </CardContent>
      </Card>

      {/* Data Freshness */}
      <Card>
        <CardHeader>
          <CardTitle>Data Information</CardTitle>
          <CardDescription>Metrics collection and update status</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="space-y-2 text-sm">
            <div className="flex justify-between">
              <span className="text-muted-foreground">Time Period</span>
              <span className="font-medium">Last 7 Days</span>
            </div>
            <div className="flex justify-between">
              <span className="text-muted-foreground">Update Frequency</span>
              <span className="font-medium">Every 60 seconds</span>
            </div>
            <div className="flex justify-between">
              <span className="text-muted-foreground">Data Source</span>
              <span className="font-medium">Babylon Genesis Testnet</span>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
