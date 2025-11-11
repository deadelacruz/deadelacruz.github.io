require 'nokogiri'

module Jekyll
  module TOCFilter
    def toc_only(input)
      doc = Nokogiri::HTML::DocumentFragment.parse(input)
      headers = doc.css('h1, h2, h3, h4, h5, h6')
      
      return '' if headers.empty?
      
      toc = '<ul>'
      prev_level = 0
      
      headers.each do |header|
        level = header.name[1].to_i
        id = header['id'] || header.text.downcase.gsub(/[^a-z0-9]+/, '-').gsub(/^-|-$/, '')
        header['id'] = id
        
        if level > prev_level
          toc += '<ul>' * (level - prev_level)
        elsif level < prev_level
          toc += '</ul>' * (prev_level - level)
        end
        
        toc += "<li><a href='##{id}'>#{header.text}</a></li>"
        prev_level = level
      end
      
      toc += '</ul>' * prev_level
      toc += '</ul>'
      
      toc
    end
  end
end

Liquid::Template.register_filter(Jekyll::TOCFilter)

