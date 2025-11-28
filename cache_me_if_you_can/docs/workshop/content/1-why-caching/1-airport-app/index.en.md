# 1.1 Explore the Sample Airport App

## Objective

Demonstrate caching benefits visually through the Airport App.

## What You'll Learn

- How to run the Airport App
- Visual demonstration of caching performance improvements
- Real-world impact of caching on user experience

## Instructions


from the cli run

```bash
uv run streamlit run airport_app.py
```

you can expect an output like this


```bash
$ uv run streamlit run airport_app.py

  You can now view your Streamlit app in your browser.

  Local URL: http://localhost:8501
  Network URL: http://10.0.4.55:8501
  External URL: http://76.49.142.98:8501
```

1. Open the url in the browser, see the landing page for the Airport App

![airport_app_01](../../../../../img/workshop/content/1-why-caching/1-airport-app/airport_app_01.png)

2. Select a flight (default 115)

![airport_app_02](../../../../../img/workshop/content/1-why-caching/1-airport-app/airport_app_02.png)

3. Click on the buttom to Get Flight Details (Simple Query)

![airport_app_03](../../../../../img/workshop/content/1-why-caching/1-airport-app/airport_app_03.png)

4. On the right side we will see the latency from the RDBMS 2.551 ms (red)

![airport_app_04](../../../../../img/workshop/content/1-why-caching/1-airport-app/airport_app_04.png)

5. Click the same button again (Simple Query)

![airport_app_05](../../../../../img/workshop/content/1-why-caching/1-airport-app/airport_app_05.png)

6. Observe the latency difference when data is fetched from the Valkey Cache 1.082ms about 50% improvement

![airport_app_06](../../../../../img/workshop/content/1-why-caching/1-airport-app/airport_app_06.png)

7. Scroll down and click twice on the button Get Manifest (3-Table JOIN)

![airport_app_07](../../../../../img/workshop/content/1-why-caching/1-airport-app/airport_app_07.png)

8. Now we can observe a more dramatic latency difference: 31.994ms from RDBMS and 2.665ms from Valkey Cache

![airport_app_08](../../../../../img/workshop/content/1-why-caching/1-airport-app/airport_app_08.png)

9. Click twice on the button Get Passenger Flights (8-Table JOIN)

![airport_app_09](../../../../../img/workshop/content/1-why-caching/1-airport-app/airport_app_09.png)

10. Observe the latency difference between running a semi-complex query with the RDBMS 222.575ms vs simple Key/Value access on Valkey Cache 1.77ms.

![airport_app_10](../../../../../img/workshop/content/1-why-caching/1-airport-app/airport_app_10.png)

11. Scroll down to see a Summary of the Caching benefits, we had a 50% cache hit and a 46.6x performance improvement

![airport_app_11](../../../../../img/workshop/content/1-why-caching/1-airport-app/airport_app_11.png)

12. Click multiple times on the 3 buttons randomly and the responses should come from the Valkey Cache with consistent responses in single digit milliseconds.

![airport_app_12](../../../../../img/workshop/content/1-why-caching/1-airport-app/airport_app_12.png)

## Key Takeaways

- Caching can dramatically reduce response times
- Visual metrics help understand performance improvements
- User experience is significantly enhanced with proper caching
