"use client";

import { useState } from "react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { api, AddressInfo, Holding, SmartMoneyScore } from "@/lib/api";
import { formatNumber } from "@/lib/utils";
import { Search, Wallet, TrendingUp, AlertCircle } from "lucide-react";

export default function AddressPage() {
  const [address, setAddress] = useState("");
  const [addressInfo, setAddressInfo] = useState<AddressInfo | null>(null);
  const [holdings, setHoldings] = useState<Record<string, Holding> | null>(null);
  const [smartMoneyScore, setSmartMoneyScore] = useState<SmartMoneyScore | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSearch() {
    if (!address.trim()) {
      setError("Please enter an address");
      return;
    }

    try {
      setLoading(true);
      setError(null);

      // Fetch all data in parallel
      const [infoData, holdingsData, smartData] = await Promise.allSettled([
        api.getAddressInfo(address),
        api.getAddressHoldings(address),
        api.getSmartMoneyScore(address),
      ]);

      if (infoData.status === "fulfilled") {
        setAddressInfo(infoData.value);
      }
      if (holdingsData.status === "fulfilled") {
        setHoldings(holdingsData.value);
      }
      if (smartData.status === "fulfilled") {
        setSmartMoneyScore(smartData.value);
      }

      if (infoData.status === "rejected") {
        setError(infoData.reason.message || "Failed to fetch address info");
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to fetch address data");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-3xl font-bold tracking-tight">Address Lookup</h1>
        <p className="text-muted-foreground">
          Search and analyze any Babylon Genesis address
        </p>
      </div>

      {/* Search Section */}
      <Card>
        <CardHeader>
          <CardTitle>Search Address</CardTitle>
          <CardDescription>
            Enter a Babylon address to view detailed analytics
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="flex gap-2">
            <Input
              placeholder="bbn1..."
              value={address}
              onChange={(e) => setAddress(e.target.value)}
              onKeyPress={(e) => {
                if (e.key === "Enter") handleSearch();
              }}
              className="font-mono"
            />
            <Button onClick={handleSearch} disabled={loading}>
              <Search className="w-4 h-4 mr-2" />
              {loading ? "Searching..." : "Search"}
            </Button>
          </div>
          {error && (
            <div className="mt-3 flex items-center gap-2 text-sm text-destructive">
              <AlertCircle className="w-4 h-4" />
              {error}
            </div>
          )}
        </CardContent>
      </Card>

      {/* Results */}
      {addressInfo && (
        <>
          {/* Address Overview */}
          <Card>
            <CardHeader>
              <div className="flex items-center justify-between">
                <div>
                  <CardTitle>Address Overview</CardTitle>
                  <code className="text-sm text-muted-foreground font-mono">
                    {address}
                  </code>
                </div>
                <Wallet className="w-5 h-5 text-muted-foreground" />
              </div>
            </CardHeader>
            <CardContent>
              <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
                <div>
                  <div className="text-sm text-muted-foreground mb-1">Transaction Count</div>
                  <div className="text-2xl font-bold">
                    {formatNumber(addressInfo.transaction_count)}
                  </div>
                </div>
                <div>
                  <div className="text-sm text-muted-foreground mb-1">Total Volume</div>
                  <div className="text-2xl font-bold">
                    {formatNumber(addressInfo.total_volume)}
                  </div>
                </div>
                <div>
                  <div className="text-sm text-muted-foreground mb-1">First Seen</div>
                  <div className="text-sm font-medium">
                    {addressInfo.first_seen
                      ? new Date(addressInfo.first_seen).toLocaleDateString()
                      : "Unknown"}
                  </div>
                </div>
                <div>
                  <div className="text-sm text-muted-foreground mb-1">Last Seen</div>
                  <div className="text-sm font-medium">
                    {addressInfo.last_seen
                      ? new Date(addressInfo.last_seen).toLocaleDateString()
                      : "Unknown"}
                  </div>
                </div>
              </div>

              {/* Labels */}
              {addressInfo.labels && addressInfo.labels.length > 0 && (
                <div className="mt-4">
                  <div className="text-sm text-muted-foreground mb-2">Labels</div>
                  <div className="flex flex-wrap gap-2">
                    {addressInfo.labels.map((label) => (
                      <Badge key={label} variant="secondary">
                        {label}
                      </Badge>
                    ))}
                  </div>
                </div>
              )}
            </CardContent>
          </Card>

          {/* Smart Money Score */}
          {smartMoneyScore && (
            <Card>
              <CardHeader>
                <div className="flex items-center justify-between">
                  <div>
                    <CardTitle>Smart Money Analysis</CardTitle>
                    <CardDescription>AI-powered behavioral scoring</CardDescription>
                  </div>
                  <TrendingUp className="w-5 h-5 text-muted-foreground" />
                </div>
              </CardHeader>
              <CardContent>
                <div className="space-y-4">
                  <div className="flex items-center justify-between">
                    <div>
                      <div className="text-sm text-muted-foreground">Smart Money Score</div>
                      <div className="text-4xl font-bold">{smartMoneyScore.score}</div>
                    </div>
                    <Badge
                      variant={
                        smartMoneyScore.rating === "ELITE"
                          ? "default"
                          : smartMoneyScore.rating === "SMART"
                          ? "secondary"
                          : "outline"
                      }
                      className="text-lg px-4 py-2"
                    >
                      {smartMoneyScore.rating}
                    </Badge>
                  </div>

                  <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
                    <div className="space-y-1">
                      <div className="text-xs text-muted-foreground">Profitability</div>
                      <div className="text-lg font-semibold">
                        {smartMoneyScore.profitability_score}
                      </div>
                    </div>
                    <div className="space-y-1">
                      <div className="text-xs text-muted-foreground">Early Adoption</div>
                      <div className="text-lg font-semibold">
                        {smartMoneyScore.early_adoption_score}
                      </div>
                    </div>
                    <div className="space-y-1">
                      <div className="text-xs text-muted-foreground">Volume</div>
                      <div className="text-lg font-semibold">
                        {smartMoneyScore.volume_score}
                      </div>
                    </div>
                    <div className="space-y-1">
                      <div className="text-xs text-muted-foreground">Win Rate</div>
                      <div className="text-lg font-semibold">
                        {smartMoneyScore.win_rate_score}
                      </div>
                    </div>
                    <div className="space-y-1">
                      <div className="text-xs text-muted-foreground">Influence</div>
                      <div className="text-lg font-semibold">
                        {smartMoneyScore.influence_score}
                      </div>
                    </div>
                  </div>
                </div>
              </CardContent>
            </Card>
          )}

          {/* Holdings */}
          {holdings && Object.keys(holdings).length > 0 && (
            <Card>
              <CardHeader>
                <CardTitle>Token Holdings</CardTitle>
                <CardDescription>Current token balances</CardDescription>
              </CardHeader>
              <CardContent>
                <div className="space-y-2">
                  {Object.entries(holdings).map(([denom, holding]) => (
                    <div
                      key={denom}
                      className="flex items-center justify-between p-3 border rounded-md"
                    >
                      <div>
                        <div className="font-medium">{denom}</div>
                        <div className="text-sm text-muted-foreground">
                          {holding.amount}
                        </div>
                      </div>
                      {holding.value_usd && (
                        <div className="text-right">
                          <div className="font-semibold">${holding.value_usd.toFixed(2)}</div>
                          <div className="text-xs text-muted-foreground">USD Value</div>
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>
          )}
        </>
      )}

      {/* Empty State */}
      {!addressInfo && !loading && !error && (
        <Card className="border-dashed">
          <CardContent className="flex flex-col items-center justify-center py-12">
            <Search className="w-12 h-12 text-muted-foreground mb-4" />
            <h3 className="text-lg font-semibold mb-2">No Address Selected</h3>
            <p className="text-sm text-muted-foreground text-center max-w-md">
              Enter a Babylon address above to view detailed analytics, smart money scores, and token holdings.
            </p>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
