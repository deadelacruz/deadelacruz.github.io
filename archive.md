---
layout: page
title: Archive
permalink: /archive
description: Browse all blog posts by date
---

<h1>Blog Archive</h1>

<div class="archive-container">
  {% assign postsByYear = site.posts | group_by_exp: "post", "post.date | date: '%Y'" %}
  {% for year in postsByYear %}
    <div class="archive-year">
      <h2>{{ year.name }}</h2>
      <ul class="archive-list">
        {% for post in year.items %}
          <li>
            <a href="{{ post.url | relative_url }}">{{ post.title }}</a>
            <span class="archive-date">{{ post.date | date: "%B %d" }}</span>
          </li>
        {% endfor %}
      </ul>
    </div>
  {% endfor %}
</div>

<style>
.archive-container {
  margin-top: 30px;
}
.archive-year {
  margin-bottom: 40px;
}
.archive-year h2 {
  color: var(--link-color);
  border-bottom: 2px solid var(--link-color);
  padding-bottom: 10px;
  margin-bottom: 20px;
}
.archive-list {
  list-style: none;
  padding: 0;
}
.archive-list li {
  padding: 10px 0;
  border-bottom: 1px solid var(--card-background-color);
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.archive-list li:last-child {
  border-bottom: none;
}
.archive-list a {
  color: var(--main-text-color);
  text-decoration: none;
  flex: 1;
}
.archive-list a:hover {
  color: var(--link-color);
}
.archive-date {
  color: var(--main-text-color);
  opacity: 0.6;
  font-size: 0.9em;
  margin-left: 20px;
}
</style>

