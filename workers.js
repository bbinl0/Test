export default {
  async fetch(request) {
    const url = new URL(request.url);
    const query = url.searchParams.get("query");

    // Your YouTube Data API key
    const YOUTUBE_API_KEY = "AIzaSyBZKN7j0rj22Da7uTbY0E-SIHSn3WGlgZ4";
    const YOUTUBE_SEARCH_API_URL = "https://www.googleapis.com/youtube/v3/search";
    const YOUTUBE_VIDEOS_API_URL = "https://www.googleapis.com/youtube/v3/videos";

    if (!query) {
      return new Response(
        JSON.stringify({
          status: false,
          message: "Query parameter is missing",
        }),
        { status: 400, headers: { "Content-Type": "application/json" } }
      );
    }

    // Determine if the query is a YouTube video URL
    const videoId = extractVideoIdFromUrl(query);

    if (videoId) {
      // Handle specific video details
      const videoData = await fetchVideoDetails(videoId, YOUTUBE_API_KEY, YOUTUBE_VIDEOS_API_URL);
      if (videoData.error) {
        return new Response(
          JSON.stringify({
            status: false,
            message: videoData.error,
          }),
          { status: 500, headers: { "Content-Type": "application/json" } }
        );
      }

      return new Response(
        JSON.stringify({
          status: true,
          creator: "API DEVELOPER @TheSmartDev & @agent",
          result: videoData,
        }),
        { headers: { "Content-Type": "application/json" } }
      );
    } else {
      // Handle search query
      const searchData = await fetchSearchData(query, YOUTUBE_API_KEY, YOUTUBE_SEARCH_API_URL);
      if (searchData.error) {
        return new Response(
          JSON.stringify({
            status: false,
            message: searchData.error,
          }),
          { status: 500, headers: { "Content-Type": "application/json" } }
        );
      }

      return new Response(
        JSON.stringify({
          status: true,
          creator: "API DEVELOPER @TheSmartDev & @agent",
          result: searchData,
        }),
        { headers: { "Content-Type": "application/json" } }
      );
    }
  },
};

// Extract video ID from YouTube URL
function extractVideoIdFromUrl(url) {
  const regex = /(?:https?:\/\/)?(?:www\.)?youtube\.com\/.*(?:v=|\/)([\w-]+)|youtu\.be\/([\w-]+)/;
  const match = regex.exec(url);
  return match ? match[1] || match[2] : null;
}

// Fetch video details from YouTube API
async function fetchVideoDetails(videoId, apiKey, apiUrl) {
  const response = await fetch(`${apiUrl}?part=snippet,statistics&id=${videoId}&key=${apiKey}`);
  if (!response.ok) {
    return { error: `Failed to fetch video details. HTTP Status Code: ${response.status}` };
  }

  const data = await response.json();
  if (!data.items || data.items.length === 0) {
    return { error: "No video found for the provided ID." };
  }

  const video = data.items[0];
  const snippet = video.snippet;
  const stats = video.statistics;

  return {
    title: snippet.title,
    channel: snippet.channelTitle,
    description: snippet.description,
    imageUrl: snippet.thumbnails.high.url,
    link: `https://youtube.com/watch?v=${video.id}`,
    views: stats.viewCount || "N/A",
    likes: stats.likeCount || "N/A",
    comments: stats.commentCount || "N/A",
  };
}

// Fetch search results from YouTube API
async function fetchSearchData(query, apiKey, apiUrl) {
  const response = await fetch(`${apiUrl}?part=snippet&q=${encodeURIComponent(query)}&type=video&maxResults=10&key=${apiKey}`);
  if (!response.ok) {
    return { error: `Failed to fetch search data. HTTP Status Code: ${response.status}` };
  }

  const data = await response.json();
  const videoIds = data.items.map((item) => item.id.videoId);

  // Fetch additional video statistics
  const statsResponse = await fetch(
    `https://www.googleapis.com/youtube/v3/videos?part=statistics&id=${videoIds.join(",")}&key=${apiKey}`
  );
  if (!statsResponse.ok) {
    return { error: `Failed to fetch video statistics. HTTP Status Code: ${statsResponse.status}` };
  }

  const statsData = await statsResponse.json();
  const statsMap = statsData.items.reduce((map, item) => {
    map[item.id] = item.statistics;
    return map;
  }, {});

  return data.items.map((item) => {
    const videoId = item.id.videoId;
    const snippet = item.snippet;
    const stats = statsMap[videoId] || {};

    return {
      title: snippet.title,
      channel: snippet.channelTitle,
      imageUrl: snippet.thumbnails.high.url,
      link: `https://youtube.com/watch?v=${videoId}`,
      views: stats.viewCount || "N/A",
      likes: stats.likeCount || "N/A",
      comments: stats.commentCount || "N/A",
    };
  });
}
