"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { api, ApiError } from "@/lib/api";
import type { NotificationChannelResponse } from "@/lib/types";
import { toast } from "sonner";
import { Bell, Mail, MessageCircle, Globe } from "lucide-react";

const CHANNEL_META: Record<
  string,
  { label: string; icon: typeof Bell; description: string }
> = {
  web_push: {
    label: "Browser Push",
    icon: Globe,
    description: "Push notifications in your browser",
  },
  email: {
    label: "Email",
    icon: Mail,
    description: "Approve or reject directly from email",
  },
  telegram: {
    label: "Telegram",
    icon: MessageCircle,
    description: "Instant notifications with inline buttons",
  },
};

export function NotificationSettings() {
  const [channels, setChannels] = useState<NotificationChannelResponse[]>([]);
  const [loading, setLoading] = useState(true);
  const [toggling, setToggling] = useState<string | null>(null);
  const [linkingTelegram, setLinkingTelegram] = useState(false);
  const [telegramLink, setTelegramLink] = useState<string | null>(null);

  const loadChannels = useCallback(async () => {
    try {
      const data = await api.listNotificationChannels();
      setChannels(data);
    } catch {
      // Ignore — channels may not be set up yet
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadChannels();
  }, [loadChannels]);

  async function handleToggle(channelType: string, currentEnabled: boolean) {
    setToggling(channelType);
    try {
      await api.updateNotificationChannel(channelType, {
        is_enabled: !currentEnabled,
      });
      await loadChannels();
      toast.success(
        `${CHANNEL_META[channelType]?.label || channelType} ${!currentEnabled ? "enabled" : "disabled"}`,
      );
    } catch (err) {
      toast.error(
        err instanceof ApiError ? err.detail : "Failed to update channel",
      );
    } finally {
      setToggling(null);
    }
  }

  async function handleDisconnect(channelType: string) {
    try {
      await api.disconnectNotificationChannel(channelType);
      await loadChannels();
      setTelegramLink(null);
      toast.success("Channel disconnected");
    } catch (err) {
      toast.error(
        err instanceof ApiError ? err.detail : "Failed to disconnect",
      );
    }
  }

  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);

  // Cleanup polling on unmount
  useEffect(() => {
    return () => {
      if (pollRef.current) clearInterval(pollRef.current);
    };
  }, []);

  function stopPolling() {
    if (pollRef.current) {
      clearInterval(pollRef.current);
      pollRef.current = null;
    }
  }

  async function handleConnectTelegram() {
    setLinkingTelegram(true);
    try {
      const data = await api.createTelegramLink();
      setTelegramLink(data.link_url);
      window.open(data.link_url, "_blank");

      // Start polling every 3s for up to 2 minutes
      stopPolling();
      let attempts = 0;
      pollRef.current = setInterval(async () => {
        attempts++;
        try {
          const updated = await api.listNotificationChannels();
          const tg = updated.find((c) => c.channel_type === "telegram");
          if (tg) {
            stopPolling();
            setChannels(updated);
            setTelegramLink(null);
            toast.success("Telegram connected!");
          } else if (attempts >= 40) {
            stopPolling();
            setTelegramLink(null);
          }
        } catch {
          // ignore polling errors
        }
      }, 3000);
    } catch (err) {
      toast.error(
        err instanceof ApiError ? err.detail : "Failed to create link",
      );
      setTelegramLink(null);
    } finally {
      setLinkingTelegram(false);
    }
  }

  async function handleEnableEmail() {
    try {
      await api.enableEmailChannel();
      await loadChannels();
      toast.success("Email notifications enabled");
    } catch (err) {
      toast.error(
        err instanceof ApiError ? err.detail : "Failed to enable email",
      );
    }
  }

  const telegramChannel = channels.find((c) => c.channel_type === "telegram");
  const emailChannel = channels.find((c) => c.channel_type === "email");

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2 text-base">
          <Bell className="h-4 w-4 text-muted-foreground" />
          Notifications
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        <p className="text-sm text-muted-foreground">
          Get notified when your AI agents request purchases. Approve or reject
          directly from any connected channel.
        </p>

        {loading ? (
          <div className="text-sm text-muted-foreground">Loading...</div>
        ) : (
          <div className="space-y-3">
            {/* Email channel */}
            {emailChannel ? (
              <ChannelRow
                channel={emailChannel}
                onToggle={() =>
                  handleToggle("email", emailChannel.is_enabled)
                }
                onDisconnect={() => handleDisconnect("email")}
                toggling={toggling === "email"}
              />
            ) : (
              <div className="flex items-center justify-between rounded-md border p-3">
                <div className="flex items-center gap-3">
                  <Mail className="h-4 w-4 text-muted-foreground" />
                  <div>
                    <p className="text-sm font-medium">Email</p>
                    <p className="text-xs text-muted-foreground">
                      Approve or reject directly from email
                    </p>
                  </div>
                </div>
                <Button size="sm" variant="outline" onClick={handleEnableEmail}>
                  Enable
                </Button>
              </div>
            )}

            {/* Telegram channel */}
            {telegramChannel ? (
              <ChannelRow
                channel={telegramChannel}
                onToggle={() =>
                  handleToggle("telegram", telegramChannel.is_enabled)
                }
                onDisconnect={() => handleDisconnect("telegram")}
                toggling={toggling === "telegram"}
              />
            ) : (
              <div className="flex items-center justify-between rounded-md border p-3">
                <div className="flex items-center gap-3">
                  <MessageCircle className="h-4 w-4 text-muted-foreground" />
                  <div>
                    <p className="text-sm font-medium">Telegram</p>
                    <p className="text-xs text-muted-foreground">
                      Instant notifications with inline buttons
                    </p>
                  </div>
                </div>
                {telegramLink ? (
                  <div className="flex flex-col items-end gap-1">
                    <p className="text-xs text-muted-foreground">
                      Waiting for connection...
                    </p>
                    <div className="flex gap-2">
                      <Button
                        size="sm"
                        variant="link"
                        className="h-auto p-0 text-xs"
                        onClick={() => window.open(telegramLink, "_blank")}
                      >
                        Open link again
                      </Button>
                      <Button
                        size="sm"
                        variant="link"
                        className="h-auto p-0 text-xs"
                        onClick={loadChannels}
                      >
                        Check status
                      </Button>
                    </div>
                  </div>
                ) : (
                  <Button
                    size="sm"
                    variant="outline"
                    onClick={handleConnectTelegram}
                    disabled={linkingTelegram}
                  >
                    {linkingTelegram ? "..." : "Connect"}
                  </Button>
                )}
              </div>
            )}

            {/* Existing connected channels that aren't email/telegram */}
            {channels
              .filter(
                (c) =>
                  c.channel_type !== "email" && c.channel_type !== "telegram",
              )
              .map((ch) => (
                <ChannelRow
                  key={ch.channel_type}
                  channel={ch}
                  onToggle={() => handleToggle(ch.channel_type, ch.is_enabled)}
                  onDisconnect={() => handleDisconnect(ch.channel_type)}
                  toggling={toggling === ch.channel_type}
                />
              ))}
          </div>
        )}
      </CardContent>
    </Card>
  );
}

function ChannelRow({
  channel,
  onToggle,
  onDisconnect,
  toggling,
}: {
  channel: NotificationChannelResponse;
  onToggle: () => void;
  onDisconnect: () => void;
  toggling: boolean;
}) {
  const meta = CHANNEL_META[channel.channel_type];
  const Icon = meta?.icon || Bell;

  return (
    <div className="flex items-center justify-between rounded-md border p-3">
      <div className="flex items-center gap-3">
        <Icon className="h-4 w-4 text-muted-foreground" />
        <div>
          <div className="flex items-center gap-2">
            <p className="text-sm font-medium">
              {meta?.label || channel.channel_type}
            </p>
            {channel.verified && (
              <Badge variant="secondary" className="text-[10px] px-1.5 py-0">
                Connected
              </Badge>
            )}
          </div>
          <p className="text-xs text-muted-foreground">
            {meta?.description || ""}
            {channel.config?.username
              ? ` (@${channel.config.username})`
              : ""}
          </p>
        </div>
      </div>
      <div className="flex items-center gap-2">
        <Button
          size="sm"
          variant={channel.is_enabled ? "default" : "outline"}
          onClick={onToggle}
          disabled={toggling}
          className="min-w-[70px]"
        >
          {toggling ? "..." : channel.is_enabled ? "On" : "Off"}
        </Button>
        <Button
          size="sm"
          variant="ghost"
          onClick={onDisconnect}
          className="text-muted-foreground hover:text-destructive"
        >
          &times;
        </Button>
      </div>
    </div>
  );
}
