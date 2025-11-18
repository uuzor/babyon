"use client";

import { useEffect, useState } from "react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { api, SmartMoneyScore } from "@/lib/api";
import { shortenAddress } from "@/lib/utils";
import { TrendingUp, Award, Target, BarChart3, Crown } from "lucide-react";

function getRatingColor(rating: string) {
  switch (rating.toLowerCase()) {
    case "elite":
      return "bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-100";
    case "smart":
      return "bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-100";
    case "above average":
      return "bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-100";
    default:
      return "bg-gray-100 text-gray-800 dark:bg-gray-900 dark:text-gray-100";
  }
}

function getRatingIcon(rating: string) {
  switch (rating.toLowerCase()) {
    case "elite":
      return <Crown className="w-4 h-4" />;
    case "smart":
      return <TrendingUp className="w-4 h-4" />;
    case "above average":
      return <Award className="w-4 h-4" />;
    default:
      return <Target className="w-4 h-4" />;
  }
}

export default function SmartMoneyPage() {
  const [smartMoney, setSmartMoney] = useState<SmartMoneyScore[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function fetchData() {
      try {
        setLoading(true);
        const data = await api.getTopSmartMoney(50);
        setSmartMoney(data);
        setError(null);
      } catch (err) {
        setError(err instanceof Error ? err.message : "Failed to fetch data");
      } finally {
        setLoading(false);
      }
    }

    fetchData();
  }, []);

  if (loading) {
    return (
      <div className="space-y-6">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Smart Money Leaderboard</h1>
          <p className="text-muted-foreground">Loading...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="space-y-6">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Smart Money Leaderboard</h1>
          <p className="text-muted-foreground">Top performing addresses</p>
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

  const topThree = smartMoney.slice(0, 3);

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-3xl font-bold tracking-tight">Smart Money Leaderboard</h1>
        <p className="text-muted-foreground">
          Top addresses ranked by composite smart money score
        </p>
      </div>

      {/* Top 3 Podium */}
      {topThree.length > 0 && (
        <div className="grid gap-4 md:grid-cols-3">
          {topThree.map((item, index) => (
            <Card key={item.address} className={index === 0 ? "border-2 border-yellow-500" : ""}>
              <CardHeader className="pb-3">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <div className={`w-8 h-8 rounded-full flex items-center justify-center ${
                      index === 0 ? "bg-yellow-500" : index === 1 ? "bg-gray-400" : "bg-amber-600"
                    }`}>
                      <span className="text-white font-bold text-sm">#{index + 1}</span>
                    </div>
                    <div className={`px-2 py-1 rounded-md text-xs font-semibold ${getRatingColor(item.rating)}`}>
                      {item.rating}
                    </div>
                  </div>
                  {index === 0 && <Crown className="w-5 h-5 text-yellow-500" />}
                </div>
              </CardHeader>
              <CardContent>
                <div className="space-y-3">
                  <div>
                    <div className="text-sm text-muted-foreground mb-1">Address</div>
                    <code className="text-sm font-mono">{shortenAddress(item.address, 8)}</code>
                  </div>
                  <div>
                    <div className="text-sm text-muted-foreground mb-1">Smart Money Score</div>
                    <div className="text-3xl font-bold">{item.score}</div>
                  </div>
                  <div className="grid grid-cols-2 gap-2 text-xs">
                    <div>
                      <div className="text-muted-foreground">Profitability</div>
                      <div className="font-semibold">{item.profitability_score}</div>
                    </div>
                    <div>
                      <div className="text-muted-foreground">Volume</div>
                      <div className="font-semibold">{item.volume_score}</div>
                    </div>
                  </div>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}

      {/* Leaderboard Table */}
      <Card>
        <CardHeader>
          <CardTitle>Full Leaderboard</CardTitle>
          <CardDescription>All addresses ranked by smart money metrics</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="space-y-2">
            {/* Table Header */}
            <div className="grid grid-cols-7 gap-4 px-4 py-3 text-sm font-medium text-muted-foreground border-b">
              <div className="col-span-1">Rank</div>
              <div className="col-span-2">Address</div>
              <div className="col-span-1 text-center">Score</div>
              <div className="col-span-1 text-center">Rating</div>
              <div className="col-span-2 text-right">Key Metrics</div>
            </div>

            {/* Table Rows */}
            {smartMoney.map((item, index) => (
              <div
                key={item.address}
                className="grid grid-cols-7 gap-4 px-4 py-3 text-sm items-center hover:bg-accent rounded-md transition-colors"
              >
                <div className="col-span-1 font-medium">#{index + 1}</div>
                <div className="col-span-2 font-mono text-xs">{shortenAddress(item.address, 6)}</div>
                <div className="col-span-1 text-center">
                  <Badge variant="outline" className="font-bold">
                    {item.score}
                  </Badge>
                </div>
                <div className="col-span-1 flex justify-center">
                  <div className={`px-2 py-1 rounded-md text-xs font-semibold flex items-center gap-1 ${getRatingColor(item.rating)}`}>
                    {getRatingIcon(item.rating)}
                    {item.rating}
                  </div>
                </div>
                <div className="col-span-2 text-right space-x-2">
                  <span className="text-xs text-muted-foreground">
                    P: {item.profitability_score}
                  </span>
                  <span className="text-xs text-muted-foreground">
                    V: {item.volume_score}
                  </span>
                  <span className="text-xs text-muted-foreground">
                    W: {item.win_rate_score}
                  </span>
                </div>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>

      {/* Scoring Explanation */}
      <Card>
        <CardHeader>
          <CardTitle>Smart Money Score Methodology</CardTitle>
          <CardDescription>How addresses are ranked</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-5">
            <div className="space-y-1">
              <div className="flex items-center gap-2">
                <TrendingUp className="w-4 h-4 text-primary" />
                <span className="text-sm font-medium">Profitability</span>
              </div>
              <p className="text-xs text-muted-foreground">Weight: 30%</p>
            </div>
            <div className="space-y-1">
              <div className="flex items-center gap-2">
                <Award className="w-4 h-4 text-primary" />
                <span className="text-sm font-medium">Early Adoption</span>
              </div>
              <p className="text-xs text-muted-foreground">Weight: 20%</p>
            </div>
            <div className="space-y-1">
              <div className="flex items-center gap-2">
                <BarChart3 className="w-4 h-4 text-primary" />
                <span className="text-sm font-medium">Volume</span>
              </div>
              <p className="text-xs text-muted-foreground">Weight: 25%</p>
            </div>
            <div className="space-y-1">
              <div className="flex items-center gap-2">
                <Target className="w-4 h-4 text-primary" />
                <span className="text-sm font-medium">Win Rate</span>
              </div>
              <p className="text-xs text-muted-foreground">Weight: 15%</p>
            </div>
            <div className="space-y-1">
              <div className="flex items-center gap-2">
                <Crown className="w-4 h-4 text-primary" />
                <span className="text-sm font-medium">Influence</span>
              </div>
              <p className="text-xs text-muted-foreground">Weight: 10%</p>
            </div>
          </div>
          <div className="mt-4 text-sm text-muted-foreground">
            <p>
              Scores range from 0-100. Ratings: Elite (75-100), Smart (60-74), Above Average (40-59), Average (0-39).
            </p>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
